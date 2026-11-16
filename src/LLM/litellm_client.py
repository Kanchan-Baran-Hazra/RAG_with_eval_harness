from typing import Optional
import litellm
from litellm import completion

# Automatically drop parameters unsupported by specific provider/model combinations
litellm.drop_params = True


class LiteLLMClient:
    """
    Unified LLM callable wrapper powered by LiteLLM.
    Supports OpenAI, Gemini, Anthropic, Groq, Ollama, or a local LiteLLM Proxy Gateway
    through one consistent interface.
    """

    def __init__(
        self,
        model: str = "gemini/gemini-3.8-flash",
        temperature: Optional[float] = 0.0,
        max_tokens: int = 1024,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key
        self.api_base = api_base

    def __call__(self, prompt: str) -> str:
        """Allows the instance to be passed directly as `llm_fn`."""
        return self.generate(prompt)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Sends a prompt via LiteLLM and returns the plain text response."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "api_key": self.api_key,
            "api_base": self.api_base,
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        response = completion(**kwargs)
        return response.choices[0].message.content.strip()


if __name__ == "__main__":
    import os
    from src.ingestion.chroma_store import VectorDBManager
    from src.retrival.rag_retriever import RAGRetriever
    from src.genrator.rag_generator import RAGGenerator
    
    # Set your provider API key (or point api_base to your local LiteLLM proxy)
    # os.environ["GEMINI_API_KEY"] = "your-api-key"
    
    # 1. Initialize LiteLLM (swap model string anytime: "gpt-4o-mini", "groq/llama-3.3-70b-versatile", "ollama/llama3.2", etc.)
    llm = LiteLLMClient(
        model="groq/openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", None),
    )
    
    # 2. Wire into Retriever (enables Multi-Query & HyDE) and Generator
    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db, llm_fn=llm)
    generator = RAGGenerator(llm_fn=llm)
    
    # 3. Run End-to-End Query
    query = "What is the annual carryover limit for unused leave?"
    chunks = retriever.retrieve(query, strategy="rerank", top_k=3)
    result = generator.generate(query, chunks)
    
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])