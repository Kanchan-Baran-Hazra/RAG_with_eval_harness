import hashlib
import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple


class ContentHasher:
    """
    Generates deterministic content hashes from string data to prevent duplicates,
    track document changes, and enrich Vector DB metadata.
    """

    def __init__(self, normalize: bool = True):
        """
        Args:
            normalize: If True, collapses extra whitespace and lowercases text before hashing
                       so trivial formatting differences still catch duplicates.
        """
        self.normalize = normalize

    def normalize_text(self, text: str) -> str:
        """Standardizes whitespace and casing for consistent content fingerprinting."""
        if not self.normalize:
            return text
        cleaned = re.sub(r"\s+", " ", text).strip().lower()
        return cleaned

    def compute_hash(self, text: str, length: int = 16) -> str:
        """Returns a deterministic SHA-256 hex digest of the string content."""
        processed = self.normalize_text(text)
        return hashlib.sha256(processed.encode("utf-8")).hexdigest()[:length]

    def compute_uuid(self, text: str) -> str:
        """
        Returns a deterministic UUID string derived purely from content.
        Ideal for Qdrant/Chroma point IDs so identical content automatically overwrites instead of duplicating.
        """
        processed = self.normalize_text(text)
        digest = hashlib.sha256(processed.encode("utf-8")).hexdigest()[:32]
        return str(uuid.UUID(digest))

    def build_hash_metadata(
        self,
        text: str,
        source_file: str,
        doc_full_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates rich hash metadata to store inside Vector DB payloads for
        deduplication awareness, audit trails, and incremental re-ingestion.
        """
        content_hash = self.compute_hash(text)
        meta: Dict[str, Any] = {
            "content_hash": content_hash,
            "content_uuid": self.compute_uuid(text),
            "source_file": source_file,
            "char_length": len(text),
        }
        if doc_full_text is not None:
            meta["doc_hash"] = self.compute_hash(doc_full_text)

        return meta

    def deduplicate_chunks(
        self,
        chunks: List[str],
        existing_hashes: Optional[Set[str]] = None,
    ) -> Tuple[List[str], List[str], int]:
        """
        Removes duplicate strings both within the current list AND against a set of
        already-indexed hashes from your Vector DB.

        Returns:
            (unique_chunks, unique_hashes, skipped_count)
        """
        seen: Set[str] = set(existing_hashes) if existing_hashes else set()
        unique_chunks: List[str] = []
        unique_hashes: List[str] = []
        skipped = 0

        for chunk in chunks:
            if not chunk or not chunk.strip():
                skipped += 1
                continue

            h = self.compute_hash(chunk)
            if h in seen:
                skipped += 1
                continue

            seen.add(h)
            unique_chunks.append(chunk)
            unique_hashes.append(h)

        return unique_chunks, unique_hashes, skipped


# --- Example Usage ---
if __name__ == "__main__":
    hasher = ContentHasher(normalize=True)

    raw_chunks = [
        "Employees receive 20 paid annual leave days per year.",
        "  Employees   receive 20 paid annual leave days per year. \n",  # Whitespace/formatting duplicate
        "Sick leave is capped at 10 days per calendar year.",
        "Employees receive 20 paid annual leave days per year.",          # Exact duplicate
    ]

    # Simulate hashes already stored in ChromaDB / Qdrant
    already_in_db = {hasher.compute_hash("Sick leave is capped at 10 days per calendar year.")}

    unique_chunks, hashes, skipped_count = hasher.deduplicate_chunks(
        chunks=raw_chunks,
        existing_hashes=already_in_db,
    )
    print(f"Already in DB: {already_in_db}")

    print(f"Kept {len(unique_chunks)} unique chunks | Skipped {skipped_count} duplicates\n")

    for chunk in unique_chunks:
        meta = hasher.build_hash_metadata(
            text=chunk,
            source_file="03_Annual_and_Sick_Leave_Policy.pdf",
        )
        print("Chunk:", chunk)
        print("Metadata:", meta)