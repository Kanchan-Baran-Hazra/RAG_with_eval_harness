# RUN
- cd RAG_with_eval_harness/evaluation/ingestion/pipe_docling/data

## Genrate the synthetic golden dataset
- python generate_gold_dataset_docling.py

- cd ..

### This line run the eval pipeline and genrate the result of the evaluation inside the eval_results folder
- python eval_docling.py



# Document Extraction Evaluation Pipeline

## 1. Overview

This module evaluates the performance and quality of PDF document extraction using **Docling**.

The main goal is to understand how efficiently Docling processes documents and identify potential extraction problems before sending the extracted content into a RAG pipeline.

The evaluation currently focuses on:

- Extraction success and failure.
- Processing time and memory consumption.
- Extracted text statistics.
- Detected document elements, such as tables and pictures.
- Text comparison using WER and CER.
- Generating JSON and CSV evaluation reports.

---

## 2. Evaluation Workflow

The current workflow:

```text
Original PDF Documents
        |
        v
  Docling Extraction
        |
        v
Synthetic Golden Dataset
        |
        v
  Evaluation Pipeline
        |
        v
  Metric Calculation
        |
        v
 JSON + CSV Reports
        |
        v
 Identify Potential Issues
```

### Step-by-step explanation

1. **Original PDF:** Provide PDF documents as input.
2. **Docling Extraction:** Docling extracts text and document elements.
3. **Synthetic Golden Dataset:** Generate reference data using Docling's extracted output.
4. **Evaluation:** Compare extracted output with the generated reference and calculate metrics.
5. **Report Generation:** Save evaluation results in JSON and CSV formats.
6. **Analysis:** Examine performance and extraction-related metrics to identify potential issues.

---

## 3. Understanding the Evaluation Metrics

The evaluation metrics are divided into three categories.

### A. Performance Metrics

These metrics measure how efficiently Docling processes documents.

| Metric | Description |
|---|---|
| `latency_sec` | Total time taken to process a document, in seconds. |
| `sec_per_page` | Average processing time per page. |
| `peak_memory_mb` | Maximum memory consumed during processing, in MB. |

**Example:**

```json
{
  "pages": 2,
  "latency_sec": 38.586,
  "sec_per_page": 19.293,
  "peak_memory_mb": 455.82
}
```

Interpretation:

- The document contains 2 pages.
- Docling took approximately 38.59 seconds to process it.
- Average processing time was approximately 19.29 seconds per page.
- Peak memory consumption was approximately 455.82 MB.

These metrics help identify slow processing and high memory consumption.

**Important:** Processing time and memory usage depend on document complexity, hardware, OCR, and other processing settings.

### B. Text Extraction Metrics

These metrics describe the extracted text.

| Metric | Description |
|---|---|
| `char_count` | Total number of extracted characters. |
| `word_count` | Total number of extracted words. |
| `is_empty_extraction` | Indicates whether the extraction returned empty or blank content. |
| `wer` | Word Error Rate. |
| `cer` | Character Error Rate. |

#### 1. Word Error Rate (WER)

WER measures the difference between extracted words and reference words.

It is calculated using:

```text
WER = (Substitutions + Deletions + Insertions)
      / Total Reference Words
```

Where:

- **Substitution:** An incorrect word replaces the correct word.
- **Deletion:** A reference word is missing.
- **Insertion:** An extra word appears in the extracted text.

A lower WER indicates better matching.

#### 2. Character Error Rate (CER)

CER measures differences at the character level.

```text
CER = (Character Substitutions
     + Character Deletions
     + Character Insertions)
     / Total Reference Characters
```

A lower CER indicates better matching.

**Important interpretation:**

```json
{
  "wer": 0.0,
  "cer": 0.0
}
```

This means the extracted text matches the reference text without measured word or character differences.

However, the current reference is generated using Docling itself. Therefore, zero WER and CER do not prove that the original PDF was extracted perfectly.

If Docling extracts an incorrect word and the synthetic reference contains the same incorrect word, the evaluation can still report zero error.

### C. Structural Extraction Metrics

These metrics describe the elements detected in the document.

| Metric | Description |
|---|---|
| `pages` | Total number of pages in the PDF. |
| `tables_detected` | Number of tables detected by Docling. |
| `pictures_detected` | Number of pictures detected by Docling. |

Example:

```json
{
  "pages": 2,
  "tables_detected": 2,
  "pictures_detected": 0
}
```

Interpretation:

Docling processed a two-page document and detected two tables and no pictures.

**Important:** Detecting two tables does not prove that their contents, rows, columns, and cell relationships are correct.

---

## 4. Understanding the JSON Evaluation Report

The JSON report stores detailed results for individual documents.

Example:

```json
{
  "file_name": "01_Code_of_Conduct_and_Ethics.pdf",
  "status": "success",
  "error": null,
  "pages": 2,
  "latency_sec": 38.586,
  "sec_per_page": 19.293,
  "peak_memory_mb": 455.82,
  "char_count": 3422,
  "word_count": 373,
  "tables_detected": 2,
  "pictures_detected": 0,
  "is_empty_extraction": false,
  "wer": 0.0,
  "cer": 0.0
}
```

### Field explanations

- `file_name`: Name of the processed PDF.
- `status`: Processing status, such as success or failure.
- `error`: Error information if processing fails.
- `pages`: Number of PDF pages.
- `latency_sec`: Total extraction time.
- `sec_per_page`: Average time per page.
- `peak_memory_mb`: Peak memory consumption.
- `char_count`: Extracted character count.
- `word_count`: Extracted word count.
- `tables_detected`: Number of detected tables.
- `pictures_detected`: Number of detected pictures.
- `is_empty_extraction`: Whether extracted content is empty.
- `wer`: Word Error Rate.
- `cer`: Character Error Rate.

JSON is useful when detailed information about a particular document is needed.

---

## 5. Understanding the CSV Evaluation Report

The CSV report provides a summary of multiple document evaluations.

Example:

```csv
file_name,status,error,pages,latency_sec,sec_per_page,peak_memory_mb,char_count,word_count,tables_detected
01_Code_of_Conduct_and_Ethics.pdf,success,"",2,38.586,19.293,455.82,3422,373,2
02_Remote_and_Hybrid_Work_Policy.pdf,success,"",2,15.457,7.729,153.58,3546,387,2
```

### Why do we need CSV?

CSV is useful for:

- Comparing processing times across documents.
- Identifying documents that consume more memory.
- Finding extraction failures.
- Comparing text extraction statistics.
- Creating charts and dashboards.
- Analysing large document collections.

JSON provides detailed individual results, while CSV provides a convenient overview of multiple documents.

---

## 6. Important Limitation: Synthetic Golden Dataset

The current evaluation uses a synthetic golden dataset generated from Docling's own output.

This creates an important limitation.

Consider this example:

**Original PDF:**

```text
Machine Learning - 3 Credits
```

**Docling extracted output:**

```text
Machine Learning - 8 Credits
```

**Synthetic golden reference:**

```text
Machine Learning - 8 Credits
```

The evaluation compares the extracted output with the synthetic reference.

Since both contain `8 Credits`, WER and CER may report zero error.

But the original PDF contains `3 Credits`.

Therefore:

**Synthetic golden data measures consistency with the generated reference, not actual extraction accuracy.**

To measure real extraction accuracy, we need an independently verified reference dataset.

---

## 7. Current Implementation Status

| Component | Status |
|---|---|
| Docling PDF extraction | Implemented |
| Synthetic golden dataset generation | Implemented |
| Evaluation pipeline | Initial implementation |
| Performance metrics | Implemented |
| Text statistics | Implemented |
| WER and CER calculation | Implemented |
| Structural metrics | Initial implementation |
| JSON report generation | Implemented |
| CSV report generation | Implemented |
| Manually verified golden dataset | Planned |
| Actual extraction accuracy evaluation | Planned |
| Advanced structural validation | Planned |
| Automated extraction error detection | Planned |

---

## 8. Future Improvements

The next improvements should focus on making the evaluation more reliable.

### 1. Page-level extraction coverage

Measure how many pages contain extracted content compared with the total number of pages.

For example:

```text
Total pages: 10
Pages with extracted content: 9
Page coverage: 90%
```

Page coverage is useful for identifying potentially missed pages, but it does not prove that every page was completely extracted.

### 2. Manually Verified Golden Dataset

Create a small collection of PDFs with manually verified reference text.

Then compare Docling's output against this independent reference.

This will help measure actual extraction accuracy.

### 3. Structural Validation

Evaluate whether:

- Expected tables are detected.
- Table rows and columns are preserved.
- Headings and paragraphs are identified.
- Content appears in the correct reading order.
- Important content is missing.

### 4. Advanced Accuracy Metrics

Consider adding:

- Table cell accuracy.
- Reading-order accuracy.
- Layout detection accuracy.
- Page-level extraction accuracy.

These metrics require suitable reference annotations.

### 5. Automated Error Detection

Identify suspicious documents using validation rules.

For example:

- Empty extraction.
- Unexpectedly low character count.
- Missing pages.
- Suspiciously low table counts.
- Extraction failures.
- Abnormal processing time or memory consumption.

These checks should flag suspicious documents for further investigation, not automatically declare them incorrect.

---

## 9. Final Goal

The long-term goal is to develop a reliable document extraction evaluation system for a production-ready RAG pipeline.

The system should:

1. Measure extraction performance.
2. Evaluate text and structural extraction quality.
3. Identify suspicious extraction results.
4. Support alternative extraction and correction.
5. Preserve document structure and source information.
6. Deliver trustworthy extracted content to the RAG ingestion pipeline.

**Current milestone:** Initial Docling evaluation with synthetic golden data and JSON/CSV reporting.

**Next milestone:** Independent ground-truth evaluation and stronger structural validation.