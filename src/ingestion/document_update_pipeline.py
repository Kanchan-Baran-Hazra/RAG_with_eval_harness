from pathlib import Path
from typing import Any, Dict, Literal, Optional


class DocumentUpdatePipeline:
    """
    Dynamically updates a single document across ChromaDB or Qdrant by filtering on
    `source_file`, comparing `doc_hash`, and replacing stale chunks only if content changed.
    """

    def __init__(self, extractor, hasher, chunker, vector_db):
        self.extractor = extractor
        self.hasher = hasher
        self.chunker = chunker
        self.vector_db = vector_db

    def update_document(
        self,
        file_path: str,
        chunk_strategy: Literal["fixed", "recursive", "markdown", "semantic", "sentence"] = "markdown",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        path = Path(file_path)
        source_file = path.name

        # 1. Extract updated file & compute new hash + UUID
        markdown_text = self.extractor.extract_file(path)
        new_doc_hash = self.hasher.compute_hash(markdown_text)
        new_doc_uuid = self.hasher.compute_uuid(f"{source_file}::{markdown_text}")

        # 2. Dynamically fetch existing records based on DB backend (Chroma vs Qdrant)
        existing_ids = []
        old_doc_hash = None

        backend = self.vector_db.backend

        if backend == "chroma":
            existing_records = self.vector_db.chroma_collection.get(
                where={"source_file": source_file},
                include=["metadatas"],
            )
            existing_ids = existing_records.get("ids", [])
            existing_metas = existing_records.get("metadatas", [])
            if existing_metas:
                old_doc_hash = existing_metas[0].get("doc_hash")

        elif backend == "qdrant":
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            q_filter = Filter(
                must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]
            )
            # Scroll through Qdrant collection to find matching points
            points, _ = self.vector_db.qdrant_client.scroll(
                collection_name=self.vector_db.collection_name,
                scroll_filter=q_filter,
                with_payload=True,
                with_vectors=False,
            )
            existing_ids = [p.id for p in points]
            if points and points[0].payload:
                old_doc_hash = points[0].payload.get("doc_hash")

        else:
            raise ValueError(f"Unknown backend: {backend}")

        # 3. Skip if document hash is identical (no actual content change)
        if old_doc_hash == new_doc_hash:
            return {
                "source_file": source_file,
                "backend": backend,
                "status": "unchanged",
                "doc_hash": new_doc_hash,
                "chunks_replaced": 0,
            }

        # 4. Hash differs (or file is new): delete previous stale chunks for this document
        if existing_ids:
            if backend == "chroma":
                self.vector_db.chroma_collection.delete(where={"source_file": source_file})
            elif backend == "qdrant":
                from qdrant_client.models import PointIdsList
                self.vector_db.qdrant_client.delete(
                    collection_name=self.vector_db.collection_name,
                    points_selector=PointIdsList(points=existing_ids),
                )

        # 5. Chunk & deduplicate the updated document
        raw_chunks = self.chunker.chunk(markdown_text, strategy=chunk_strategy)
        unique_chunks, _, skipped = self.hasher.deduplicate_chunks(chunks=raw_chunks)

        # 6. Store updated chunks using the appropriate upsert method
        indexed = 0
        if unique_chunks:
            meta = {
                "doc_uuid": new_doc_uuid,
                "doc_hash": new_doc_hash,
                "chunk_strategy": chunk_strategy,
            }
            if extra_metadata:
                meta.update(extra_metadata)

            if backend == "chroma":
                indexed = self.vector_db.upsert_chroma(
                    chunks=unique_chunks,
                    source_file=source_file,
                    extra_metadata=meta,
                )
            else:
                indexed = self.vector_db.upsert_qdrant(
                    chunks=unique_chunks,
                    source_file=source_file,
                    extra_metadata=meta,
                )

        return {
            "source_file": source_file,
            "backend": backend,
            "status": "updated" if existing_ids else "inserted_new",
            "old_doc_hash": old_doc_hash,
            "new_doc_hash": new_doc_hash,
            "old_chunks_deleted": len(existing_ids),
            "new_chunks_indexed": indexed,
            "duplicates_skipped": skipped,
        }


# --- Example Usage ---
if __name__ == "__main__":
    from src.ingestion.extract_file import DoclingExtractor
    from src.ingestion.content_hasher import ContentHasher
    from src.ingestion.chunker import TextChunker
    from src.ingestion.chroma_store import VectorDBManager

    # Works for chroma or qdrant seamlessly
    db_manager = VectorDBManager(backend="qdrant", qdrant_url="http://localhost:6333", collection_name="policies_prod1")

    updater = DocumentUpdatePipeline(
        extractor=DoclingExtractor(do_ocr=False, do_table_structure=True),
        hasher=ContentHasher(normalize=True),
        chunker=TextChunker(chunk_size=800, chunk_overlap=120),
        vector_db=db_manager,
    )

    result = updater.update_document(
        file_path=r"docs\03_Annual_and_Sick_Leave_Policy.pdf",
        chunk_strategy="markdown",
        extra_metadata={"department": "HR"},
    )
    print(result)
























# from pathlib import Path
# from typing import Any, Dict, Literal, Optional


# class DocumentUpdatePipeline:
#     """
#     Updates a single document in ChromaDB by filtering on `source_file`,
#     comparing `doc_hash`, and replacing stale chunks only if the content changed.
#     """

#     def __init__(self, extractor, hasher, chunker, vector_db):
#         self.extractor = extractor
#         self.hasher = hasher
#         self.chunker = chunker
#         self.vector_db = vector_db

#     def update_document(
#         self,
#         file_path: str,
#         chunk_strategy: Literal["fixed", "recursive", "markdown", "semantic", "sentence"] = "markdown",
#         extra_metadata: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         path = Path(file_path)
#         source_file = path.name

#         # 1. Extract updated file & compute new hash + UUID
#         markdown_text = self.extractor.extract_file(path)
#         new_doc_hash = self.hasher.compute_hash(markdown_text)
#         new_doc_uuid = self.hasher.compute_uuid(f"{source_file}::{markdown_text}")

#         # 2. Filter Vector DB by document name (`source_file`)
#         existing_records = self.vector_db.chroma_collection.get(
#             where={"source_file": source_file},
#             include=["metadatas"],
#         )

#         existing_ids = existing_records.get("ids", [])
#         existing_metas = existing_records.get("metadatas", [])
#         old_doc_hash = existing_metas[0].get("doc_hash") if existing_metas else None

#         # 3. Skip if document hash is identical (no actual content change)
#         if old_doc_hash == new_doc_hash:
#             return {
#                 "source_file": source_file,
#                 "status": "unchanged",
#                 "doc_hash": new_doc_hash,
#                 "chunks_replaced": 0,
#             }

#         # 4. Hash differs (or file is new): delete previous chunks for this document
#         if existing_ids:
#             self.vector_db.chroma_collection.delete(where={"source_file": source_file})

#         # 5. Chunk & deduplicate the updated document
#         raw_chunks = self.chunker.chunk(markdown_text, strategy=chunk_strategy)
#         unique_chunks, _, skipped = self.hasher.deduplicate_chunks(chunks=raw_chunks)

#         # 6. Store updated chunks in ChromaDB
#         indexed = 0
#         if unique_chunks:
#             meta = {
#                 "doc_uuid": new_doc_uuid,
#                 "doc_hash": new_doc_hash,
#                 "chunk_strategy": chunk_strategy,
#             }
#             if extra_metadata:
#                 meta.update(extra_metadata)

#             indexed = self.vector_db.upsert_chroma(
#                 chunks=unique_chunks,
#                 source_file=source_file,
#                 extra_metadata=meta,
#             )

#         return {
#             "source_file": source_file,
#             "status": "updated" if existing_ids else "inserted_new",
#             "old_doc_hash": old_doc_hash,
#             "new_doc_hash": new_doc_hash,
#             "old_chunks_deleted": len(existing_ids),
#             "new_chunks_indexed": indexed,
#             "duplicates_skipped": skipped,
#         }


# # --- Example Usage ---
# if __name__ == "__main__":
    # from src.ingestion.extract_file import DoclingExtractor
    # from src.ingestion.content_hasher import ContentHasher
    # from src.ingestion.chunker import TextChunker
    # from src.ingestion.chroma_store import VectorDBManager

#     updater = DocumentUpdatePipeline(
#         extractor=DoclingExtractor(do_ocr=False, do_table_structure=True),
#         hasher=ContentHasher(normalize=True),
#         chunker=TextChunker(chunk_size=800, chunk_overlap=120),
#         vector_db=VectorDBManager(backend="qdrant", qdrant_url="http://localhost:6333", collection_name="policies_prod1"),
#     )

#     result = updater.update_document(
#         file_path=r"docs\03_Annual_and_Sick_Leave_Policy.pdf",
#         chunk_strategy="markdown",
#         extra_metadata={"department": "HR"},
#     )
#     print(result)