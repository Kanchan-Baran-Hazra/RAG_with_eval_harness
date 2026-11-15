from pathlib import Path
from typing import Dict, List, Union

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions


class DoclingExtractor:
    """Clean wrapper around Docling to extract Markdown text from documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".png", ".jpg", ".jpeg"}

    def __init__(self, do_ocr: bool = False, do_table_structure: bool = True):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = do_ocr
        pipeline_options.do_table_structure = do_table_structure

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def extract_file(self, file_path: Union[str, Path]) -> str:
        """Extracts and returns Markdown text from a single document."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        result = self.converter.convert(str(path))
        return result.document.export_to_markdown()

    def extract_folder(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path, None] = None,
    ) -> Dict[str, str]:
        """
        Extracts Markdown from all supported documents in a folder.
        Optionally saves each extracted document as <filename>.md in output_dir.
        Returns a dictionary mapping {file_name: markdown_text}.
        """
        in_path = Path(input_dir)
        if not in_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {in_path}")

        files: List[Path] = sorted(
            f for f in in_path.iterdir()
            if f.is_file() and f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        )

        if not files:
            raise ValueError(f"No supported documents found in {in_path}")

        out_path = Path(output_dir) if output_dir else None
        if out_path:
            out_path.mkdir(parents=True, exist_ok=True)

        extracted_docs: Dict[str, str] = {}

        for file in files:
            md_text = self.extract_file(file)
            extracted_docs[file.name] = md_text

            if out_path:
                md_file = out_path / f"{file.stem}.md"
                md_file.write_text(md_text, encoding="utf-8")

        return extracted_docs


# --- Example Usage ---
if __name__ == "__main__":
    extractor = DoclingExtractor(do_ocr=False, do_table_structure=True)

    # 1. Extract a single file
    single_md = extractor.extract_file(r"docs\01_Code_of_Conduct_and_Ethics.pdf")
    print(f"Extracted {len(single_md)} characters from single file.")
    print("=============================================================\n")
    print(type(single_md))

    # 2. Extract an entire folder and save matching .md files
    # all_docs = extractor.extract_folder(
    #     input_dir="docs",
    #     output_dir="extracted_md",
    # )
    # print(f"Extracted {len(all_docs)} documents total.")
    # print("=============================================================")
    # print(all_docs)