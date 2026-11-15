from typing import List, Literal, Optional
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)


class TextChunker:
    """Unified chunking utility supporting multiple strategies. Takes raw text and returns List[str]."""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self._semantic_splitter = None  # Lazy-loaded only if semantic chunking is called

    def fixed_size(self, text: str) -> List[str]:
        """1. Splits text at a fixed character count with overlap."""
        splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return splitter.split_text(text)

    def recursive(self, text: str) -> List[str]:
        """2. Recursively splits by headings, paragraphs, lines, and words."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )
        return splitter.split_text(text)

    def markdown_header(self, text: str) -> List[str]:
        """3. Splits by Markdown headings (#, ##, ###) and sub-splits oversized sections."""
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ]
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
        header_docs = md_splitter.split_text(text)

        sub_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        final_docs = sub_splitter.split_documents(header_docs)
        return [doc.page_content for doc in final_docs]

    def semantic(self, text: str, percentile_threshold: int = 90) -> List[str]:
        """4. Splits where embedding similarity between consecutive sentences drops."""
        if self._semantic_splitter is None:
            from langchain_experimental.text_splitter import SemanticChunker
            from langchain_huggingface import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
            self._semantic_splitter = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=percentile_threshold,
            )
        return self._semantic_splitter.split_text(text)

    def sentence_window(self, text: str, sentences_per_chunk: int = 4, overlap_sentences: int = 1) -> List[str]:
        """5. Groups sentences into sliding windows to preserve exact sentence boundaries."""
        import re

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if not sentences:
            return []

        step = max(1, sentences_per_chunk - overlap_sentences)
        return [
            " ".join(sentences[i : i + sentences_per_chunk])
            for i in range(0, len(sentences), step)
        ]

    def chunk(
        self,
        text: str,
        strategy: Literal["fixed", "recursive", "markdown", "semantic", "sentence"] = "markdown",
    ) -> List[str]:
        """Single entry point: pass text and strategy name, get List[str] back."""
        strategies = {
            "fixed": self.fixed_size,
            "recursive": self.recursive,
            "markdown": self.markdown_header,
            "semantic": self.semantic,
            "sentence": self.sentence_window,
        }
        if strategy not in strategies:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {list(strategies.keys())}")
        return strategies[strategy](text)


# --- Example Usage ---
if __name__ == "__main__":
    sample_text = """# Remote Work Policy

## Core Hours
Employees must be available online between 10:00 AM and 3:00 PM IST. Meetings should be scheduled inside this window whenever possible.

## Equipment Allowance
Full-time staff receive an annual stipend to maintain a reliable home workstation and high-speed internet connection.
"""

    chunker = TextChunker(chunk_size=300, chunk_overlap=50)

    # Call via unified method:
    md_chunks = chunker.chunk(sample_text, strategy="markdown")
    rec_chunks = chunker.chunk(sample_text, strategy="recursive")
    sem_chunks = chunker.chunk(sample_text, strategy="semantic")
    sent_chunks = chunker.chunk(sample_text, strategy="sentence")

    print(f"Markdown chunks: {len(md_chunks)}", md_chunks)
    print("=====================")
    print(f"Recursive chunks {len(rec_chunks)}:", rec_chunks)
    print("=====================")
    print(f"Semantic chunks: {len(sem_chunks)}", sem_chunks)
    print("=====================")
    print(f"Sentence chunks: {len(sent_chunks)}", sent_chunks)
    print("=====================")