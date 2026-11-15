from pathlib import Path
from typing import Any, Dict, Literal, Optional


class RAGIngestionPipeline:
    """Integrates existing classes using extract_file() per document with unique file UUIDs & hashes."""

    def __init__(self, extractor, hasher, chunker, vector_db):
        self.extractor = extractor
        self.hasher = hasher
        self.chunker = chunker
        self.vector_db = vector_db

    def run(
        self,
        input_dir: str = "docs",
        chunk_strategy: Literal["fixed", "recursive", "markdown", "semantic", "sentence"] = "markdown",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Processes files one-by-one via extract_file(), assigns unique file UUID + hash, and stores in Chroma."""
        in_path = Path(input_dir)
        files = sorted(
            f for f in in_path.iterdir()
            if f.is_file() and f.suffix.lower() in self.extractor.SUPPORTED_EXTENSIONS
        )

        seen_hashes = set()
        summary = {"files_processed": 0, "chunks_indexed": 0, "duplicates_skipped": 0}

        for file_path in files:
            # 1. Extract single file using extract_file()
            markdown_text = self.extractor.extract_file(file_path)

            # 2. Generate unique UUID & hash specific to this file + content
            doc_uuid = self.hasher.compute_uuid(f"{file_path.name}::{markdown_text}")
            doc_hash = self.hasher.compute_hash(markdown_text)

            # 3. Chunk the extracted Markdown
            raw_chunks = self.chunker.chunk(markdown_text, strategy=chunk_strategy)

            # 4. Deduplicate chunks across and within files
            unique_chunks, unique_hashes, skipped = self.hasher.deduplicate_chunks(
                chunks=raw_chunks,
                existing_hashes=seen_hashes,
            )
            seen_hashes.update(unique_hashes)

            # 5. Store in local ChromaDB with unique doc_uuid and doc_hash in metadata
            if unique_chunks:
                meta = {
                    "doc_uuid": doc_uuid,
                    "doc_hash": doc_hash,
                    "chunk_strategy": chunk_strategy,
                }
                if extra_metadata:
                    meta.update(extra_metadata)

                indexed = self.vector_db.upsert_qdrant(
                    chunks=unique_chunks,
                    source_file=file_path.name,
                    extra_metadata=meta,
                )
            else:
                indexed = 0

            summary["files_processed"] += 1
            summary["chunks_indexed"] += indexed
            summary["duplicates_skipped"] += skipped

            print(f"[{file_path.name}] doc_uuid: {doc_uuid} | doc_hash: {doc_hash} | indexed: {indexed}")

        return summary


# --- Example Usage ---
if __name__ == "__main__":
    from src.ingestion.extract_file import DoclingExtractor
    from src.ingestion.content_hasher import ContentHasher
    from src.ingestion.chunker import TextChunker
    from src.ingestion.chroma_store import VectorDBManager

    pipeline = RAGIngestionPipeline(
        extractor=DoclingExtractor(do_ocr=False, do_table_structure=True),
        hasher=ContentHasher(normalize=True),
        chunker=TextChunker(chunk_size=800, chunk_overlap=120),
        vector_db=VectorDBManager(backend="qdrant", qdrant_url="http://localhost:6333", collection_name="policies_prod1"),
    )

    stats = pipeline.run(
        input_dir="docs",
        chunk_strategy="markdown",
        extra_metadata={"department": "HR"},
    )
    print("\nSummary:", stats)






































# from typing import Any, Dict, Literal, Optional


# class RAGIngestionPipeline:
#     """Integrates your existing extractor, hasher, chunker, and vector_db instances into one flow."""

#     def __init__(self, extractor, hasher, chunker, vector_db):
#         self.extractor = extractor
#         self.hasher = hasher
#         self.chunker = chunker
#         self.vector_db = vector_db

#     def run(
#         self,
#         input_dir: str = "docs",
#         chunk_strategy: Literal["fixed", "recursive", "markdown", "semantic", "sentence"] = "markdown",
#         save_extracted_md_dir: Optional[str] = None,
#         extra_metadata: Optional[Dict[str, Any]] = None,
#     ) -> Dict[str, Any]:
#         """Runs Extract -> Hash -> Chunk -> Deduplicate -> Vector DB Upsert."""
#         extracted_docs = self.extractor.extract_folder(
#             input_dir=input_dir,
#             output_dir=save_extracted_md_dir,
#         )

#         seen_hashes = set()
#         summary = {"files_processed": 0, "chunks_indexed": 0, "duplicates_skipped": 0}

#         for filename, markdown_text in extracted_docs.items():
#             doc_hash = self.hasher.compute_hash(markdown_text)
#             raw_chunks = self.chunker.chunk(markdown_text, strategy=chunk_strategy)

#             unique_chunks, unique_hashes, skipped = self.hasher.deduplicate_chunks(
#                 chunks=raw_chunks,
#                 existing_hashes=seen_hashes,
#             )
#             seen_hashes.update(unique_hashes)

#             if unique_chunks:
#                 meta = {"doc_hash": doc_hash, "chunk_strategy": chunk_strategy}
#                 if extra_metadata:
#                     meta.update(extra_metadata)

#                 indexed = self.vector_db.upsert(
#                     chunks=unique_chunks,
#                     source_file=filename,
#                     extra_metadata=meta,
#                 )
#             else:
#                 indexed = 0

#             summary["files_processed"] += 1
#             summary["chunks_indexed"] += indexed
#             summary["duplicates_skipped"] += skipped

#         return summary


# # --- Example Usage with Your Existing Classes ---
# if __name__ == "__main__":
    # from src.ingestion.extract_file import DoclingExtractor
    # from src.ingestion.content_hasher import ContentHasher
    # from src.ingestion.chunker import TextChunker
    # from src.ingestion.chroma_store import VectorDBManager

#     pipeline = RAGIngestionPipeline(
#         extractor=DoclingExtractor(do_ocr=False, do_table_structure=True),
#         hasher=ContentHasher(normalize=True),
#         chunker=TextChunker(chunk_size=800, chunk_overlap=120),
#         vector_db=VectorDBManager(backend="chroma", collection_name="rag_policies"),
#     )

#     stats = pipeline.run(
#         input_dir="docs",
#         chunk_strategy="markdown",
#         extra_metadata={"department": "HR"},
#     )
#     print(stats)