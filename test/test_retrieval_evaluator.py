from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter

load_dotenv()  # Load environment variables from .env file

# 1. Define the Structured Output Schema
class EvaluationResult(BaseModel):
    score: int = Field(
        ..., 
        description="Score from 1 to 5. 5 means the retrieved context completely covers the ground truth; 1 means it contains none of the required facts."
    )
    is_supported: bool = Field(
        ..., 
        description="True if the core facts of the ground truth are present in the retrieved context, False otherwise."
    )
    # missing_facts: list[str] = Field(
    #     default_factory=list, 
    #     description="List of specific facts present in the ground truth that are missing from the retrieved context."
    # )
    reason: str = Field(
        ..., 
        description="A concise, step-by-step explanation justifying the score."
    )


# 1. Pace requests: 1 request every 12 seconds (~5 RPM) to stay safely under the 8K TPM ceiling
rate_limiter = InMemoryRateLimiter(
    requests_per_second=1 / 12,  # 1 request per 12 seconds
    check_every_n_seconds=0.5,
    max_bucket_size=1,  # Prevent bursting multiple requests at once
)

# 2. Universal Model Wrapper!
# Easily swap between "groq:llama-3.3-70b-versatile", "google_genai:gemini-2.5-flash", "openai:gpt-4o-mini", etc.
llm = init_chat_model(
    "groq:openai/gpt-oss-120b",
    temperature=0.0,
    rate_limiter=rate_limiter,
).with_retry(
    stop_after_attempt=5,
    wait_exponential_jitter=True,  # Automatically backs off on 429 TPM errors
)
structured_llm = llm.with_structured_output(EvaluationResult)

# 3. Create the Prompt Template
eval_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an impartial search and retrieval evaluator. "
        "Compare the 'Ground Truth' against the 'Retrieved Context'. "
        "Determine if the Retrieved Context contains enough information to derive the Ground Truth. "
        "Do not use outside knowledge; rely strictly on the provided text."
    )),
    ("human", "Ground Truth:\n{ground_truth}\n\nRetrieved Context:\n{retrieved_context}")
])

# 4. Build the Evaluation Chain (LCEL)
eval_chain = eval_prompt | structured_llm

def evaluate_retrieval(ground_truth: str, retrieved_context: str) -> EvaluationResult:
    """Wrapper function to invoke the LangChain evaluator."""
    return eval_chain.invoke({
        "ground_truth": ground_truth,
        "retrieved_context": retrieved_context
    })

# --- Example Usage ---
if __name__ == "__main__":
    golden = "Project Apollo was started in 1961 and successfully landed the first humans on the Moon in July 1969."
    context = "In July 1969, NASA's Apollo 11 mission landed Neil Armstrong and Buzz Aldrin on the lunar surface."
    
    result = evaluate_retrieval(ground_truth=golden, retrieved_context=context)
    
    print(result.model_dump_json(indent=2))