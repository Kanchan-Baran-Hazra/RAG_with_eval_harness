import re
from typing import Any, Callable, Dict, List, Literal, Optional
import numpy as np


class RAGRetriever:
    """
    Unified Retrieval Engine supporting Dense, Sparse (BM25), Hybrid (RRF),
    MMR Diversity, Cross-Encoder Reranking, Multi-Query Expansion, and HyDE.
    Works directly on top of your existing VectorDBManager (ChromaDB or Qdrant).
    """

    def __init__(
        self,
        vector_db,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        llm_fn: Optional[Callable[[str], str]] = None,
    ):
        """
        Args:
            vector_db: Your initialized VectorDBManager instance.
            reranker_model: HuggingFace Cross-Encoder model for post-retrieval reranking.
            llm_fn: Optional callable `fn(prompt: str) -> str` for Multi-Query & HyDE.
        """
        self.vector_db = vector_db
        self.reranker_model_name = reranker_model
        self.llm_fn = llm_fn

        # Lazy-loaded models (only loaded into RAM if their method is called)
        self._reranker = None
        self._bm25 = None
        self._corpus_records: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Internal Helpers (Corpus Sync & Lazy Model Loading)
    # -------------------------------------------------------------------------
    def _load_corpus_from_db(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetches stored chunks from ChromaDB or Qdrant for BM25 keyword indexing."""
        records: List[Dict[str, Any]] = []

        if self.vector_db.backend == "chroma":
            where_clause = None
            if filters:
                conds = [{k: {"$eq": v}} for k, v in filters.items()]
                where_clause = conds[0] if len(conds) == 1 else {"$and": conds}

            res = self.vector_db.chroma_collection.get(
                where=where_clause,
                include=["documents", "metadatas"],
            )
            for doc, meta in zip(res.get("documents", []), res.get("metadatas", [])):
                records.append({"text": doc, "metadata": meta})

        elif self.vector_db.backend == "qdrant":
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            q_filter = None
            if filters:
                q_filter = Filter(
                    must=[FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filters.items()]
                )

            points, _ = self.vector_db.qdrant_client.scroll(
                collection_name=self.vector_db.collection_name,
                scroll_filter=q_filter,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                payload = p.payload or {}
                records.append({
                    "text": payload.get("text", ""),
                    "metadata": {k: v for k, v in payload.items() if k != "text"},
                })

        return records

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.reranker_model_name)
        return self._reranker

    # -------------------------------------------------------------------------
    # 1. Dense Vector Search (Semantic)
    # -------------------------------------------------------------------------
    def dense_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Standard semantic cosine-similarity search via VectorDBManager."""
        return self.vector_db.search(query=query, top_k=top_k, filters=filters)

    # -------------------------------------------------------------------------
    # 2. Sparse Keyword Search (BM25)
    # -------------------------------------------------------------------------
    def sparse_bm25_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Exact lexical keyword retrieval using BM25."""
        from rank_bm25 import BM25Okapi

        records = self._load_corpus_from_db(filters=filters)
        if not records:
            return []

        tokenized_corpus = [self._tokenize(r["text"]) for r in records]
        bm25 = BM25Okapi(tokenized_corpus)

        scores = bm25.get_scores(self._tokenize(query))
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "text": records[idx]["text"],
                    "metadata": records[idx]["metadata"],
                    "score": round(float(scores[idx]), 4),
                })
        return results

    # -------------------------------------------------------------------------
    # 3. Hybrid Search (Dense + BM25 fused with Reciprocal Rank Fusion)
    # -------------------------------------------------------------------------
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Combines Dense and Sparse BM25 rankings using Reciprocal Rank Fusion (RRF)."""
        dense_hits = self.dense_search(query=query, top_k=top_k * 3, filters=filters)
        sparse_hits = self.sparse_bm25_search(query=query, top_k=top_k * 3, filters=filters)

        fused_scores: Dict[str, float] = {}
        chunk_lookup: Dict[str, Dict[str, Any]] = {}

        for rank, hit in enumerate(dense_hits, start=1):
            key = hit["text"]
            chunk_lookup[key] = hit
            fused_scores[key] = fused_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        for rank, hit in enumerate(sparse_hits, start=1):
            key = hit["text"]
            chunk_lookup[key] = hit
            fused_scores[key] = fused_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        ranked_keys = sorted(fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True)[:top_k]

        return [
            {
                "text": chunk_lookup[k]["text"],
                "metadata": chunk_lookup[k]["metadata"],
                "score": round(fused_scores[k], 5),
            }
            for k in ranked_keys
        ]

    # -------------------------------------------------------------------------
    # 4. Maximal Marginal Relevance (MMR - Relevance + Diversity)
    # -------------------------------------------------------------------------
    def mmr_search(
        self,
        query: str,
        top_k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.6,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Balances query relevance with chunk diversity (lambda_mult: 1.0 = pure relevance, 0.0 = max diversity).
        """
        candidates = self.dense_search(query=query, top_k=fetch_k, filters=filters)
        if len(candidates) <= top_k:
            return candidates

        query_emb = self.vector_db.embedder.encode(query, normalize_embeddings=True)
        doc_embs = self.vector_db.embedder.encode(
            [c["text"] for c in candidates], normalize_embeddings=True
        )

        selected_indices: List[int] = []
        remaining_indices = list(range(len(candidates)))

        for _ in range(top_k):
            best_idx = None
            best_mmr_score = -float("inf")

            for idx in remaining_indices:
                relevance = float(np.dot(query_emb, doc_embs[idx]))
                diversity_penalty = (
                    max(float(np.dot(doc_embs[idx], doc_embs[s])) for s in selected_indices)
                    if selected_indices
                    else 0.0
                )
                mmr_score = lambda_mult * relevance - (1 - lambda_mult) * diversity_penalty

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = idx

            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)

        return [
            {
                "text": candidates[i]["text"],
                "metadata": candidates[i]["metadata"],
                "score": candidates[i]["score"],
            }
            for i in selected_indices
        ]

    # -------------------------------------------------------------------------
    # 5. Two-Stage Cross-Encoder Reranking
    # -------------------------------------------------------------------------
    def rerank_search(
        self,
        query: str,
        top_k: int = 5,
        initial_k: int = 20,
        use_hybrid: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves broad candidates via Hybrid/Dense search, then rescores with a Cross-Encoder."""
        candidates = (
            self.hybrid_search(query=query, top_k=initial_k, filters=filters)
            if use_hybrid
            else self.dense_search(query=query, top_k=initial_k, filters=filters)
        )
        if not candidates:
            return []

        reranker = self._get_reranker()
        pairs = [(query, c["text"]) for c in candidates]
        rerank_scores = reranker.predict(pairs)

        scored_candidates = [
            {
                "text": c["text"],
                "metadata": c["metadata"],
                "score": round(float(score), 4),
            }
            for c, score in zip(candidates, rerank_scores)
        ]
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:top_k]

    # -------------------------------------------------------------------------
    # 6. Multi-Query Expansion (Pre-Retrieval LLM Rewriting)
    # -------------------------------------------------------------------------
    def multi_query_search(
        self,
        query: str,
        top_k: int = 5,
        num_queries: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generates multiple query phrasings via `llm_fn`, searches all, and fuses results."""
        if not self.llm_fn:
            raise ValueError("Pass `llm_fn` when initializing RAGRetriever to use multi_query_search.")

        prompt = (
            f"Generate {num_queries} distinct search query variations to retrieve policy documents "
            f"answering the question below. Return one query per line without numbering.\n\n"
            f"Original question: {query}"
        )
        raw_output = self.llm_fn(prompt)
        queries = [query] + [q.strip("-•1234567890. ") for q in raw_output.splitlines() if q.strip()]

        seen_texts: Dict[str, Dict[str, Any]] = {}
        for q in queries[: num_queries + 1]:
            for hit in self.hybrid_search(query=q, top_k=top_k, filters=filters):
                key = hit["text"]
                if key not in seen_texts or hit["score"] > seen_texts[key]["score"]:
                    seen_texts[key] = hit

        return sorted(seen_texts.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    # -------------------------------------------------------------------------
    # 7. HyDE (Hypothetical Document Embeddings)
    # -------------------------------------------------------------------------
    def hyde_search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generates a hypothetical policy excerpt via `llm_fn` and searches using its embedding."""
        if not self.llm_fn:
            raise ValueError("Pass `llm_fn` when initializing RAGRetriever to use hyde_search.")

        prompt = (
            "Write a short, formal company policy paragraph that directly answers the question below.\n\n"
            f"Question: {query}"
        )
        hypothetical_doc = self.llm_fn(prompt)
        return self.dense_search(query=hypothetical_doc, top_k=top_k, filters=filters)

    # -------------------------------------------------------------------------
    # Unified Single Entry Point
    # -------------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        strategy: Literal["dense", "sparse", "hybrid", "mmr", "rerank", "multi_query", "hyde"] = "hybrid",
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Single dispatcher method to run any retrieval strategy."""
        strategies = {
            "dense": self.dense_search,
            "sparse": self.sparse_bm25_search,
            "hybrid": self.hybrid_search,
            "mmr": self.mmr_search,
            "rerank": self.rerank_search,
            "multi_query": self.multi_query_search,
            "hyde": self.hyde_search,
        }
        if strategy not in strategies:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {list(strategies.keys())}")
        return strategies[strategy](query=query, top_k=top_k, filters=filters)


# --- Example Usage ---
if __name__ == "__main__":
    from src.ingestion.chroma_store import VectorDBManager
    from src.LLM.litellm_client import LiteLLMClient
    import os

    # 1. Initialize LiteLLM (swap model string anytime: "gpt-4o-mini", "groq/llama-3.3-70b-versatile", "ollama/llama3.2", etc.)
    llm = LiteLLMClient(
        model="groq/openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", None),
    )

    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db,llm_fn=llm)

    query = "What is the Governance Roles in the cumpany?"

    # 1. Hybrid Search (Dense + BM25 RRF)
    # hybrid_hits = retriever.retrieve(query, strategy="hybrid", top_k=3)

    # # 2. Hybrid + Cross-Encoder Reranking (Highest Accuracy)
    # reranked_hits = retriever.retrieve(query, strategy="rerank", top_k=3)

    # # 3. MMR Diverse Search with Metadata Filter
    # diverse_hits = retriever.retrieve(
    #     query,
    #     strategy="mmr",
    #     top_k=3,
    #     filters={"source_file": "03_Annual_and_Sick_Leave_Policy.pdf"},
    # )

    reranked_hits = retriever.retrieve(query, strategy="hyde", top_k=3)

    for h in reranked_hits:
        print(f"[Score: {h['score']}] {h['metadata'].get('source_file')} -> {h['text'][:150]}...")