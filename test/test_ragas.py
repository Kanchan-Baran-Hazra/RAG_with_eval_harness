
import json
import re
import httpx

from ragas.llms.base import InstructorBaseRagasLLM


class FastAPIRagasLLM(InstructorBaseRagasLLM):

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.timeout = 120

    def _extract_content(self, data):
        return data["response"]["content"]

    def _parse_response(self, content, response_model):

        print("\n========== RAW MODEL RESPONSE ==========")
        print(repr(content))
    
        print("\n========== EXPECTED RESPONSE SCHEMA ==========")
        print(response_model.model_json_schema())
    
        print("========================================\n")

    # Keep your existing parsing code temporarily

        # Remove optional Markdown code fences
        content = content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        # Extract JSON if the model adds extra text
        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                f"Model did not return valid JSON: {content}"
            )

        json_text = content[start:end + 1]

        return response_model.model_validate_json(json_text)

    
    def generate(self, prompt: str, response_model):
    
        schema = response_model.model_json_schema()
    
        final_prompt = f"""
    You are a structured data extraction system.
    
    TASK:
    Follow the evaluation instructions below.
    
    EVALUATION INSTRUCTIONS:
    {prompt}
    
    OUTPUT REQUIREMENTS:
    Return ONE JSON object containing the evaluation result.
    
    The required JSON structure is:
    {json.dumps(schema, indent=2)}
    
    IMPORTANT:
    - Do not return the schema itself.
    - Do not copy the example or schema.
    - Fill in the required fields with your actual evaluation.
    - Return JSON only.
    """
    
        response = httpx.post(
            self.endpoint,
            json={"prompt": final_prompt},
            timeout=self.timeout
        )
    
        response.raise_for_status()
    
        content = self._extract_content(response.json())
    
        print("RAW OUTPUT:", content)
    
        return self._parse_response(content, response_model)
    
    
    async def agenerate(self, prompt: str, response_model):
    
        schema = response_model.model_json_schema()
    
        final_prompt = f"""
    You are a structured data extraction system.
    
    TASK:
    Follow the evaluation instructions below.
    
    EVALUATION INSTRUCTIONS:
    {prompt}
    
    OUTPUT REQUIREMENTS:
    Return ONE JSON object containing the evaluation result.
    
    The required JSON structure is:
    {json.dumps(schema, indent=2)}
    
    IMPORTANT:
    - Do not return the schema itself.
    - Do not copy the example or schema.
    - Fill in the required fields with your actual evaluation.
    - Return JSON only.
    """
    
        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:
    
            response = await client.post(
                self.endpoint,
                json={"prompt": final_prompt}
            )
    
            response.raise_for_status()
    
        content = self._extract_content(response.json())
    
        print("RAW OUTPUT:", content)
    
        return self._parse_response(content, response_model)
    


# from fastapi_ragas_llm import FastAPIRagasLLM
from ragas.metrics.collections import ContextRecall
import time

evaluator_llm = FastAPIRagasLLM(
    endpoint="http://192.168.29.171:8000/generate"
)

metric = ContextRecall(llm=evaluator_llm)

retrieved_contexts = [
    "The conflict of interest disclosure rule enforces a $50 gift cap.",
    "Employees must report workplace harassment through the ethics hotline."
]

start = time.perf_counter()

result = metric.score(
    user_input="What is the maximum monetary gift cap under the conflict of interest disclosure rules?",
    retrieved_contexts=retrieved_contexts,
    reference="The conflict of interest disclosure rule enforces a $50 gift cap."
)

end = time.perf_counter()

print("Context Recall:", result.value)
print("Evaluation latency:", round(end - start, 2), "seconds")



































# from openai import OpenAI
# from ragas.llms import llm_factory

# client = OpenAI(
#     api_key="ollama",
#     base_url="http://localhost:11434/v1"
# )

# evaluator_llm = llm_factory(
#     "llama3.2:latest",
#     provider="openai",
#     client=client
# )

# retrieved_contexts = [
#     "The conflict of interest disclosure rule enforces a $50 gift cap.",
#     "Employees must report workplace harassment through the ethics hotline."
# ]

# from ragas.metrics.collections import ContextRecall

# metric = ContextRecall(llm=evaluator_llm)
# import time

# start = time.perf_counter()
# result = metric.score(
#     user_input="What is the maximum monetary gift cap under the conflict of interest disclosure rules?",
#     retrieved_contexts=retrieved_contexts,
#     reference="The conflict of interest disclosure rule enforces a $50 gift cap."
# )


# end = time.perf_counter()


# print("Evaluation latency:", round(end - start, 2), "seconds")
# print("Context Recall:", result.value)
# print("Reason:", result)






























# import json
# from datasets import Dataset
# from ragas import evaluate,RunConfig
# from ragas.metrics import LLMContextPrecisionWithReference, LLMContextRecall
# from ragas.llms import LangchainLLMWrapper
# from langchain_litellm import ChatLiteLLM

# from src.ingestion.chroma_store import VectorDBManager
# from src.retrival.rag_retriever import RAGRetriever

# # 1. Configure Ragas Judge LLM via langchain-litellm
# judge_llm = LangchainLLMWrapper(
#     ChatLiteLLM(model="gemini/gemini-3.8-flash", drop_params=True)
# )

# # 2. Initialize Your Retriever
# db = VectorDBManager(backend="chroma", collection_name="rag_policies")
# retriever = RAGRetriever(vector_db=db)

# # 3. Load Golden Dataset & Collect Retrieved Chunks
# with open("eval_dataset/test_gold.json", "r", encoding="utf-8") as f:
#     raw_dataset = json.load(f)

# eval_rows = {
#     "user_input": [],
#     "retrieved_contexts": [],
#     "reference": [],
# }

# for item in raw_dataset:
#     if item.get("query_type") == "unanswerable_negative" or not item.get("source_documents"):
#         continue

#     query = item["question"]
#     ground_truth = item["ground_truth"]
#     chunks = retriever.retrieve(query, strategy="hybrid", top_k=5)

#     eval_rows["user_input"].append(query)
#     eval_rows["retrieved_contexts"].append([c["text"] for c in chunks])
#     eval_rows["reference"].append(ground_truth)

# ragas_dataset = Dataset.from_dict(eval_rows)

# # 4. Initialize evaluate()-compatible Metrics
# metrics = [
#     LLMContextPrecisionWithReference(llm=judge_llm),
#     LLMContextRecall(llm=judge_llm),
# ]

# # 5. Run Evaluation
# results = evaluate(
#     dataset=ragas_dataset.select(range(2)),  # Test on 2 rows first
#     metrics=metrics,
#     run_config=RunConfig(max_workers=1, timeout=60),
#     raise_exceptions=True,
# )

# print("\n=== Ragas Retrieval Scores ===")
# print(results)

# df = results.to_pandas()
# df.to_csv("ragas_retrieval_results.csv", index=False)



