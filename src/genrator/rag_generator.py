from typing import Any, Callable, Dict, List


class RAGGenerator:
    """
    Simple grounded RAG generator that formats retrieved chunks into a prompt
    and generates an answer using any provided LLM callable.
    """

    def __init__(self, llm_fn: Callable[[str], str]):
        """
        Args:
            llm_fn: Any callable function that takes a prompt string and returns the LLM text response.
                    (e.g., an OpenAI, Gemini, Ollama, or LiteLLM wrapper function).
        """
        self.llm_fn = llm_fn

    def _build_prompt(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks with source metadata into a clean, grounded prompt."""
        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk.get("metadata", {}).get("source_file", "Unknown Source")
            text = chunk.get("text", "").strip()
            context_blocks.append(f"[{idx}] (Source: {source})\n{text}")

        formatted_context = "\n\n---\n\n".join(context_blocks)

        return f"""You are a helpful policy assistant. Answer the user's question using ONLY the context provided below.
If the answer cannot be found in the context, respond with: "I cannot find this information in the provided documents."
Do not guess or use outside knowledge.

### Context:
{formatted_context}

### Question:
{query}

### Answer:"""

    def generate(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates a grounded response from retrieved chunks and returns the answer + sources."""
        if not retrieved_chunks:
            return {
                "query": query,
                "answer": "I cannot find this information in the provided documents.",
                "sources": [],
            }

        prompt = self._build_prompt(query, retrieved_chunks)
        answer = self.llm_fn(prompt).strip()

        # Extract unique source filenames used
        sources = list(
            dict.fromkeys(
                c.get("metadata", {}).get("source_file", "Unknown")
                for c in retrieved_chunks
            )
        )

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
        }


# --- Example Usage ---
if __name__ == "__main__":
    from src.ingestion.chroma_store import VectorDBManager
    from src.retrival.rag_retriever import RAGRetriever

    # Example LLM wrapper (replace with your Gemini / OpenAI / Ollama / LiteLLM call)
    def dummy_llm(prompt: str) -> str:
        # e.g., return client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
        return "Full-time employees receive 20 paid annual leave days per year."

    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db)
    generator = RAGGenerator(llm_fn=dummy_llm)

    query = "How many annual leave days do full-time employees get?"
    chunks = retriever.retrieve(query, strategy="hybrid", top_k=3)
    result = generator.generate(query, chunks)

    print("Answer:", result["answer"])
    print("Sources:", result["sources"])