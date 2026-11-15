import hashlib
import uuid
from typing import Any, Dict, List, Literal, Optional

""" start qdrant server with docker:
    docker run -p 6333:6333 -v "${PWD}/qdrant_storage:/qdrant/storage" qdrant/qdrant"""


class VectorDBManager:
    """
    Unified Vector Store supporting both Local (ChromaDB) and Production (Qdrant) backends.
    Uses a shared local SentenceTransformer model so embeddings stay consistent across environments.
    """

    def __init__(
        self,
        backend: Literal["chroma", "qdrant"] = "chroma",
        collection_name: str = "rag_policies",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        # Chroma-specific
        chroma_persist_dir: str = "./chroma_db",
        # Qdrant-specific (pass url="http://localhost:6333" or Qdrant Cloud URL + api_key)
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
    ):
        self.backend = backend
        self.collection_name = collection_name

        # Shared embedding model for consistent vector representations across dev & prod
        from sentence_transformers import SentenceTransformer

        self.embedder = SentenceTransformer(embedding_model)
        self.vector_size = self.embedder.get_sentence_embedding_dimension()

        if self.backend == "chroma":
            self._init_chroma(chroma_persist_dir)
        elif self.backend == "qdrant":
            self._init_qdrant(qdrant_url, qdrant_api_key)
        else:
            raise ValueError(f"Unsupported backend: {backend}. Use 'chroma' or 'qdrant'.")

    # -------------------------------------------------------------------------
    # Backend Initializers
    # -------------------------------------------------------------------------
    def _init_chroma(self, persist_dir: str) -> None:
        import chromadb

        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _init_qdrant(self, url: str, api_key: Optional[str]) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self.qdrant_client = QdrantClient(url=url, api_key=api_key)

        if not self.qdrant_client.collection_exists(self.collection_name):
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def _make_deterministic_uuid(self, source_file: str, chunk_index: int, text: str) -> str:
        """Generates a valid UUIDv5 string (required by Qdrant and valid in Chroma)."""
        raw = f"{source_file}::{chunk_index}::{text[:100]}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        return str(uuid.UUID(digest))

    # -------------------------------------------------------------------------
    # 1. Local DB Method (ChromaDB)
    # -------------------------------------------------------------------------
    def upsert_chroma(
        self,
        chunks: List[str],
        source_file: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Embeds and upserts chunks into local ChromaDB."""
        if not chunks:
            return 0

        embeddings = self.embedder.encode(chunks, normalize_embeddings=True).tolist()
        ids, metadatas = [], []

        for idx, text in enumerate(chunks):
            ids.append(self._make_deterministic_uuid(source_file, idx, text))
            meta = {"source_file": source_file, "chunk_index": idx}
            if extra_metadata:
                meta.update(extra_metadata)
            metadatas.append(meta)

        self.chroma_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    # -------------------------------------------------------------------------
    # 2. Production DB Method (Qdrant)
    # -------------------------------------------------------------------------
    def upsert_qdrant(
        self,
        chunks: List[str],
        source_file: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Embeds and upserts chunks into production Qdrant."""
        if not chunks:
            return 0

        from qdrant_client.models import PointStruct

        embeddings = self.embedder.encode(chunks, normalize_embeddings=True).tolist()
        points = []

        for idx, (text, vector) in enumerate(zip(chunks, embeddings)):
            point_id = self._make_deterministic_uuid(source_file, idx, text)
            payload = {
                "text": text,
                "source_file": source_file,
                "chunk_index": idx,
            }
            if extra_metadata:
                payload.update(extra_metadata)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        return len(chunks)

    # -------------------------------------------------------------------------
    # Unified Router & Search
    # -------------------------------------------------------------------------
    def upsert(
        self,
        chunks: List[str],
        source_file: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Automatically routes ingestion to the configured backend."""
        if self.backend == "chroma":
            return self.upsert_chroma(chunks, source_file, extra_metadata)
        return self.upsert_qdrant(chunks, source_file, extra_metadata)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Unified similarity search with exact key-value metadata filtering across both DBs.
        Example `filters`: {"source_file": "02_Remote_and_Hybrid_Work_Policy.pdf"}
        """
        query_vector = self.embedder.encode(query, normalize_embeddings=True).tolist()

        if self.backend == "chroma":
            where_clause = None
            if filters:
                conditions = [{k: {"$eq": v}} for k, v in filters.items()]
                where_clause = conditions[0] if len(conditions) == 1 else {"$and": conditions}

            res = self.chroma_collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
            if not res["documents"] or not res["documents"][0]:
                return []

            return [
                {"text": doc, "metadata": meta, "score": round(1 - dist, 4)}
                for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
            ]

        else:  # Qdrant
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            qdrant_filter = None
            if filters:
                qdrant_filter = Filter(
                    must=[
                        FieldCondition(key=k, match=MatchValue(value=v))
                        for k, v in filters.items()
                    ]
                )

            hits = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
            ).points

            return [
                {
                    "text": hit.payload.get("text", ""),
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                    "score": round(hit.score, 4),
                }
                for hit in hits
            ]


# --- Example Usage ---
if __name__ == "__main__":
    sample_chunks = [
        "Employees must be available during core hours from 10:00 AM to 3:00 PM.",
        "Full-time employees receive 20 days of paid annual leave per calendar year.",
    ]

    # 1. Local Development / Evaluation Mode (ChromaDB)
    local_db = VectorDBManager(backend="chroma", collection_name="policies_eval")
    local_db.upsert_chroma(sample_chunks, source_file="02_Remote_Policy.pdf", extra_metadata={"dept": "HR"})
    print("Chroma Results:", local_db.search("What are the core working hours?", filters={"dept": "HR"}))

    # 2. Production Mode (Qdrant - requires local Docker container or Qdrant Cloud URL)
    prod_db = VectorDBManager(backend="qdrant", qdrant_url="http://localhost:6333", collection_name="policies_prod")
    prod_db.upsert_qdrant(sample_chunks, source_file="02_Remote_Policy.pdf", extra_metadata={"dept": "HR"})
    print("Qdrant Results:", prod_db.search("What are the core working hours?", filters={"dept": "HR"}))