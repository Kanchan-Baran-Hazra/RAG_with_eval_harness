from src.retrival.rag_retriever import RAGRetriever
from src.ingestion.chroma_store import VectorDBManager
from src.genrator.rag_generator import RAGGenerator
from src.LLM.litellm_client import LiteLLMClient
import os

# 1. Initialize LiteLLM (swap model string anytime: "gpt-4o-mini", "groq/llama-3.3-70b-versatile", "ollama/llama3.2", etc.)
llm = LiteLLMClient(
    model="groq/openai/gpt-oss-20b",
    api_key=os.getenv("GROQ_API_KEY", None),
)

# 2. Wire into Retriever (enables Multi-Query & HyDE) and Generator
db = VectorDBManager(backend="chroma", collection_name="rag_policies")
retriever = RAGRetriever(vector_db=db, llm_fn=llm)
generator = RAGGenerator(llm_fn=llm)

def _run(query: str,strategy: str = "rerank", top_k: int = 3) -> str:

    chunks = retriever.retrieve(query, strategy=strategy, top_k=top_k)
    result = generator.generate(query, chunks)
    return result


if __name__ == "__main__":
    # 3. Run End-to-End Query
    query = "What is the annual carryover limit for unused leave?"
    print(_run(query))