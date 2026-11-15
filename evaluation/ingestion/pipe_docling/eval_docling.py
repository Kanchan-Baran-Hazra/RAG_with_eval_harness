import os
import time
import json
import tracemalloc
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
from jiwer import wer, cer
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions


class DoclingEvaluator:
    def __init__(self, do_ocr: bool = True, do_table_structure: bool = True):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = do_ocr
        pipeline_options.do_table_structure = do_table_structure

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def _compute_text_metrics(self, predicted: str, reference: str) -> Dict[str, float]:
        """Computes WER and CER if ground truth text is available."""
        # Normalize whitespace to avoid penalizing minor newline differences
        pred_norm = " ".join(predicted.split())
        ref_norm = " ".join(reference.split())

        if not ref_norm:
            return {"wer": None, "cer": None}

        return {
            "wer": round(wer(ref_norm, pred_norm), 4),
            "cer": round(cer(ref_norm, pred_norm), 4),
        }

    def evaluate_file(
        self, file_path: Path, ground_truth_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Runs conversion on a single file and records performance + quality metrics."""
        tracemalloc.start()
        start_time = time.perf_counter()

        status = "success"
        error_msg = None
        md_output = ""
        num_pages = 0
        num_tables = 0
        num_pictures = 0

        try:
            result = self.converter.convert(str(file_path))
            doc = result.document
            md_output = doc.export_to_markdown()

            num_pages = len(doc.pages) if hasattr(doc, "pages") else 0
            num_tables = len(doc.tables) if hasattr(doc, "tables") else 0
            num_pictures = len(doc.pictures) if hasattr(doc, "pictures") else 0

        except Exception as e:
            status = "failed"
            error_msg = str(e)

        elapsed_sec = round(time.perf_counter() - start_time, 3)
        _, peak_mem_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mem_mb = round(peak_mem_bytes / (1024 * 1024), 2)
        char_count = len(md_output)
        word_count = len(md_output.split())
        sec_per_page = round(elapsed_sec / num_pages, 3) if num_pages > 0 else elapsed_sec

        metrics = {
            "file_name": file_path.name,
            "status": status,
            "error": error_msg,
            "pages": num_pages,
            "latency_sec": elapsed_sec,
            "sec_per_page": sec_per_page,
            "peak_memory_mb": peak_mem_mb,
            "char_count": char_count,
            "word_count": word_count,
            "tables_detected": num_tables,
            "pictures_detected": num_pictures,
            "is_empty_extraction": char_count == 0,
            "wer": None,
            "cer": None,
        }

        # Check if a matching ground truth .md file exists (e.g., doc1.pdf -> doc1.md)
        if status == "success" and ground_truth_dir:
            gt_file = ground_truth_dir / f"{file_path.stem}.md"
            if gt_file.exists():
                gt_text = gt_file.read_text(encoding="utf-8")
                accuracy = self._compute_text_metrics(md_output, gt_text)
                metrics.update(accuracy)

        return metrics, md_output

    def run_benchmark(
        self,
        input_dir: str,
        output_dir: str = "eval_results",
        ground_truth_dir: Optional[str] = None,
    ) -> pd.DataFrame:
        input_path = Path(input_dir)
        out_path = Path(output_dir)
        extracted_md_dir = out_path / "extracted_markdown"
        extracted_md_dir.mkdir(parents=True, exist_ok=True)

        gt_path = Path(ground_truth_dir) if ground_truth_dir else None
        supported_exts = {".pdf", ".docx", ".pptx", ".html", ".png", ".jpg"}
        files = [f for f in input_path.iterdir() if f.suffix.lower() in supported_exts]

        if not files:
            raise ValueError(f"No supported documents found in {input_dir}")

        all_results: List[Dict[str, Any]] = []

        print(f"Starting Docling evaluation on {len(files)} files...\n")
        for f in files:
            print(f"Processing: {f.name}...")
            metrics, md_text = self.evaluate_file(f, gt_path)
            all_results.append(metrics)

            # Save extracted markdown for manual inspection or downstream RAG chunking eval
            if metrics["status"] == "success":
                (extracted_md_dir / f"{f.stem}.md").write_text(md_text, encoding="utf-8")

        df = pd.DataFrame(all_results)

        # Save full JSON and CSV reports
        df.to_csv(out_path / "docling_eval_report.csv", index=False)
        with open(out_path / "docling_eval_report.json", "w", encoding="utf-8") as jf:
            json.dump(all_results, jf, indent=2)

        self._print_summary(df)
        return df

    def _print_summary(self, df: pd.DataFrame):
        print("\n" + "=" * 50)
        print("DOCLING EVALUATION SUMMARY")
        print("=" * 50)
        print(f"Total Files Processed : {len(df)}")
        print(f"Success Rate          : {(df['status'] == 'success').mean() * 100:.1f}%")
        print(f"Avg Latency / Doc     : {df['latency_sec'].mean():.2f}s")
        print(f"Avg Latency / Page    : {df['sec_per_page'].mean():.2f}s")
        print(f"Total Tables Detected : {df['tables_detected'].sum()}")
        print(f"Empty Extractions     : {df['is_empty_extraction'].sum()}")

        if df["wer"].notna().any():
            print(f"Mean Word Error Rate  : {df['wer'].mean():.4f} (Lower is better)")
            print(f"Mean Char Error Rate  : {df['cer'].mean():.4f} (Lower is better)")
        print("=" * 50)


if __name__ == "__main__":
    # Example folder structure:
    # data/raw_docs/       -> Put your test PDFs/DOCX here
    # data/ground_truth/   -> (Optional) Put matching .md files here for WER/CER scoring
    evaluator = DoclingEvaluator(do_ocr=True, do_table_structure=True)
    evaluator.run_benchmark(
        input_dir="data/raw_docs",
        output_dir="eval_results",
        ground_truth_dir="data/ground_truth",  # Set to None if you don't have ground truth yet  else "data/ground_truth"
    )