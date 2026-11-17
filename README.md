# 🛡️ Enterprise Policy RAG & Evaluation Harness

> An enterprise-focused Retrieval-Augmented Generation (RAG) application for company policy documents, featuring LangGraph-based guardrails, multi-strategy retrieval, automated evaluation, observability, and an administrative control center.

## 📌 Overview

Traditional RAG applications can struggle in enterprise environments because of three major problems:

1. **Retrieval inaccuracies:** Semantic search may miss exact policy identifiers, monetary limits, dates, and compliance requirements.
2. **Security and scope control:** Unrestricted queries and prompt injection attempts can lead to irrelevant processing or unsafe responses.
3. **Lack of evaluation:** Changes to chunking, retrieval strategies, or prompts can reduce answer quality without being detected.

This project addresses these challenges through a modular RAG architecture with configurable retrieval strategies, LangGraph-based query routing, evaluation benchmarking, and administrative monitoring.

The goal is to build a reliable and measurable company-policy assistant rather than simply another document chatbot.

## 🏗️ System Architecture

```text
                 ┌──────────────────────────────┐
                 │       Client / UI            │
                 └──────────────┬───────────────┘
                                │
                         POST /api/chat
                                │
                 ┌──────────────▼───────────────┐
                 │       FastAPI Backend        │
                 └──────────────┬───────────────┘
                                │
                 ┌──────────────▼───────────────┐
                 │   LangGraph Guardrail Router │
                 │                              │
                 │  Regex + LLM Classification  │
                 └──────────────┬───────────────┘
                                │
                   ┌────────────┼─────────────┐
                   │            │             │
                 Blocked      Direct          RAG
                   │            │             │
             ┌─────▼────┐ ┌─────▼────┐ ┌──────▼──────────┐
             │  Refusal │ │ Direct   │ │ Retrieval       │
             │ Response │ │ Response │ │ Dense / BM25    │
             └─────┬────┘ └─────┬────┘ │ Hybrid / HyDE   │
                   │            │      └──────┬──────────┘
                   │            │             │
                   │            │      ┌──────▼──────────┐
                   │            │      │ Grounded Answer │
                   │            │      │ Generation      │
                   │            │      └──────┬──────────┘
                   └────────────┴─────────────┘
                                │
                 ┌──────────────▼───────────────┐
                 │     SQLite Audit & Feedback  │
                 │     Admin Control Center     │
                 └──────────────────────────────┘

             LangSmith: End-to-end tracing and monitoring
             Evaluation Harness: Retrieval and answer quality
```

## ✨ Key Features

### 1. Document Ingestion and Structure-Aware Chunking

**Problem:** Basic text splitting can break policy sections, numbered clauses, tables, and headings, causing important context to be lost.

**Implementation:**
- PDF extraction using Docling.
- Structure-aware chunking using HybridChunker.
- Preservation of section hierarchy and document metadata.
- Metadata such as source file, department, and section title.

The objective is to preserve the relationships between policy sections and their supporting content.

### 2. Multi-Strategy Retrieval

A modular retrieval system supports different retrieval approaches.

| Strategy | Description |
|---|---|
| Dense retrieval | Semantic similarity using vector embeddings |
| BM25 | Lexical retrieval for exact terms and identifiers |
| Hybrid retrieval | Combines dense and sparse retrieval |
| RRF | Reciprocal Rank Fusion for combining ranked results |
| HyDE | Uses a hypothetical document representation to improve retrieval for certain queries |

**Dense retrieval:** Uses sentence embeddings such as all-MiniLM-L6-v2 or BGE-small with ChromaDB.

**Sparse retrieval:** Uses BM25 to find exact terms, policy codes, numbers, and keywords.

**Hybrid retrieval:** Combines dense and sparse rankings using Reciprocal Rank Fusion.

**HyDE:** Generates a hypothetical policy-style passage and uses its embedding to search for relevant documents.

The strategies are designed to be independently configurable and evaluated.

### 3. LangGraph-Based Guardrails and Query Routing

**Problem:** Every query should not automatically enter the complete RAG pipeline. Some requests are irrelevant, potentially malicious, or do not require document retrieval.

**Implementation:** A LangGraph StateGraph manages query classification and routing through two stages.

**Tier 1 — Rule-based filtering**
- Regex-based detection of known prompt injection patterns.
- Detection of system prompt extraction attempts.
- Early rejection of known unsafe query patterns.

**Tier 2 — LLM-based classification**

A structured LLM router classifies incoming queries into:

| Route | Purpose |
|---|---|
| `rag` | Queries requiring company policy retrieval |
| `direct` | Queries eligible for a direct response |
| `blocked` | Unsafe or disallowed requests |

Pydantic structured outputs are used for classification.

The routing design avoids sending every incoming query through retrieval and generation.

### 4. Resource-Aware Model and Embedding Design

The system is designed with constrained local hardware in mind.

Key decisions:

- Local embedding models for document indexing and query encoding.
- Lightweight 384-dimensional embedding models such as MiniLM and BGE.
- External inference through Groq using LiteLLM for supported reasoning and classification tasks.
- CPU-only PyTorch dependencies for a smaller Docker image.

The architecture separates embedding workloads from LLM inference to manage local resource consumption.

### 5. Observability and Feedback

**LangSmith integration**

LangSmith tracing is used to inspect:
- LangGraph execution.
- Retrieval and generation stages.
- Retrieved documents and scores.
- Model execution and latency.
- End-to-end pipeline behavior.

**SQLite telemetry**

The application persists interaction information, including:

- User query.
- Selected route.
- Generated answer.
- Retrieved sources.
- Request latency.
- User feedback.

**Admin Control Center**

The administrative interface provides a place to inspect application activity, review feedback, and manage knowledge-base documents.

### 6. Automated RAG Evaluation Harness

An evaluation harness is included to measure retrieval and answer quality across different strategies.

It uses a curated golden dataset of company-policy question-and-answer examples.

**Retrieval metrics**
- Hit Rate@K
- Mean Reciprocal Rank (MRR@K)
- Context Precision

**Generation metrics**
- Faithfulness
- Answer Relevancy
- End-to-end latency

The evaluation harness supports comparison of retrieval configurations and helps detect quality regressions.

## 📊 Evaluation and Benchmarking

The system supports experiments across different retrieval strategies using a consistent evaluation dataset.

### Retrieval Strategy Comparison

**Configuration:** `top_k = 3`

| Strategy | Hit Rate@3 | MRR@3 | Context Precision | Faithfulness | Answer Relevancy | Hallucinations | Avg. Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | 40% | 45% | 50% | 53% | 50% | 15% | [Pending] |
| Dense | 80% | 75% | 95% | 95% | 95% | 10% | [Pending] |
| Hybrid | 80% | 75% | 95% | 95% | 95% | 10% | [Pending] |
| HyDE + Dense | 80% | 70% | 85% | 75% | 85% | 10% | [Pending] |
| HyDE | 40% | 45% | 50% | 53% | 50% | 15% | [Pending] |
| MMR | 80% | 75% | 95% | 95% | 95% | 10% | [Pending] |
| Multu_Quary | 80% | 75% | 95% | 95% | 95% | 10% | [Pending] |


### Evaluation Objectives

The benchmark is intended to answer questions such as:

- Does hybrid retrieval improve exact policy information retrieval?
- Does reranking improve the relevance of retrieved contexts?
- Does HyDE improve retrieval for vague or conversational queries?
- Does a retrieval improvement also improve answer faithfulness?
- What is the latency cost of each retrieval strategy?

The final retrieval configuration should be selected using measured quality and latency rather than assumptions.

## 🧰 Technology Stack

| Category | Technologies |
|---|---|
| Backend | FastAPI |
| Workflow orchestration | LangGraph, LangChain Core |
| LLM integration | LiteLLM, Groq |
| Document processing | Docling, HybridChunker |
| Vector database | ChromaDB | Qdrant
| Dense embeddings | Sentence-Transformers, MiniLM, BGE |
| Sparse retrieval | Rank-BM25 |
| Data validation | Pydantic v2 |
| Persistence | SQLAlchemy, SQLite |
| Observability | LangSmith |
| Evaluation | Custom RAG Evaluation Harness |
| Deployment | Docker, Python 3.13-slim |

## 📂 Project Structure

```text
RAG_with_eval_harness/
├── .deepeval
├── admin_panel
│   ├── admin_dashboard_preview.html
├── chroma_db
├── docs
│   ├── 01_Code_of_Conduct_and_Ethics.pdf
│   ├── 02_Remote_and_Hybrid_Work_Policy.pdf
│   ├── 03_Annual_and_Sick_Leave_Policy.pdf
├── eval_dataset
│   ├── golden_source
│   │   ├── 01_Code_of_Conduct_and_Ethics.pdf
│   │   ├── 02_Remote_and_Hybrid_Work_Policy.pdf
│   │   ├── 03_Annual_and_Sick_Leave_Policy.pdf
│   │   ├── 04_Parental_and_Family_Leave_Policy.pdf
│   │   ├── 05_Information_Security_and_Access_Control.pdf
│   │   ├── 06_Generative_AI_and_LLM_Usage_Policy.pdf
│   │   ├── 07_Data_Classification_and_Privacy_Policy.pdf
│   │   ├── 08_Security_Incident_and_Breach_Response.pdf
│   │   ├── 09_Travel_and_Expense_Reimbursement_Policy.pdf
│   │   ├── 10_Home_Office_and_Equipment_Stipend.pdf
│   ├── golden.json
│   ├── test_gold.json
├── evaluation
│   ├── genrator
│   │   ├── __init__.py
│   │   ├── gen_eval_results.html
│   │   ├── gen_eval_results.json
│   │   ├── gen_html_reporter.py
│   │   ├── generation_evaluator.py
│   ├── ingestion
│   │   ├── pipe_docling
│   │   │   ├── data
│   │   │   │   ├── ground_truth
│   │   │   │   │   ├── 01_Code_of_Conduct_and_Ethics.md
│   │   │   │   │   ├── 02_Remote_and_Hybrid_Work_Policy.md
│   │   │   │   │   ├── 03_Annual_and_Sick_Leave_Policy.md
│   │   │   │   ├── raw_docs
│   │   │   │   │   ├── 01_Code_of_Conduct_and_Ethics.pdf
│   │   │   │   │   ├── 02_Remote_and_Hybrid_Work_Policy.pdf
│   │   │   │   │   ├── 03_Annual_and_Sick_Leave_Policy.pdf
│   │   │   │   ├── generate_gold_dataset_docling.py
│   │   │   ├── eval_results
│   │   │   │   ├── extracted_markdown
│   │   │   │   │   ├── 01_Code_of_Conduct_and_Ethics.md
│   │   │   │   │   ├── 02_Remote_and_Hybrid_Work_Policy.md
│   │   │   │   │   ├── 03_Annual_and_Sick_Leave_Policy.md
│   │   │   │   ├── docling_eval_report.csv
│   │   │   │   ├── docling_eval_report.json
│   │   │   ├── eval_docling.py
│   │   │   ├── README.md
│   │   ├── __init__.py
│   ├── retrival
│   │   ├── BM25
│   │   │   ├── eval_results_hybrid_k3.html
│   │   │   ├── eval_results_hybrid_k3.json
│   │   │   ├── runner.py
│   │   ├── Hybrid
│   │   │   ├── eval_results_hybrid_k3.html
│   │   │   ├── eval_results_hybrid_k3.json
│   │   │   ├── runner.py
│   │   ├── HyDE
│   │   │   ├── eval_results_hybrid_k3.html
│   │   │   ├── eval_results_hybrid_k3.json
│   │   │   ├── runner.py
│   │   ├── MMR
│   │   │   ├── eval_results_hybrid_k3.html
│   │   │   ├── eval_results_hybrid_k3.json
│   │   │   ├── runner.py
│   │   ├── Multi_Query
│   │   │   ├── eval_results_hybrid_k3.html
│   │   │   ├── eval_results_hybrid_k3.json
│   │   │   ├── runner.py
│   │   ├── Semantic
│   │   │   ├── eval_results_dense_k3.html
│   │   │   ├── eval_results_dense_k3.json
│   │   │   ├── runner.py
│   │   ├── __init__.py
│   │   ├── eval_results_hybrid_k3.html
│   │   ├── eval_results_hybrid_k3.json
│   │   ├── html_reporter.py
│   │   ├── retrieval_evaluator.py
│   │   ├── run_eval.py
├── qdrant_storage
├── src
│   ├── api
│   │   ├── db
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   ├── Feedback
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── router.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── test_main.py
│   ├── genrator
│   │   ├── __init__.py
│   │   ├── rag_generator.py
│   ├── ingestion
│   │   ├── __init__.py
│   │   ├── chroma_store.py
│   │   ├── chunker.py
│   │   ├── content_hasher.py
│   │   ├── document_update_pipeline.py
│   │   ├── extract_file.py
│   │   ├── ingestion_pipeline.py
│   ├── LLM
│   │   ├── __init__.py
│   │   ├── litellm_client.py
│   ├── retrival
│   │   ├── __init__.py
│   │   ├── rag_retriever.py
│   ├── __init__.py
│   ├── guardrails.py
│   ├── pipeline.py
│   ├── workflow.py
├── test
│   ├── __init__.py
│   ├── docling_test.py
│   ├── test_deepeval.py
│   ├── test_ragas.py
│   ├── test_retrieval_evaluator.py
├── .env
├── .gitignore
├── .python-version
├── Dockerfile
├── LICENSE
├── main.py
├── pyproject.toml
├── rag_feedback.db
├── README.md
├── requirements.txt
├── uv.lock
```

*Note: The directory names and files above reflect the documented project structure. Adjust them to match the actual repository.*

## 🚀 Getting Started

### Prerequisites

- Python 3.13
- Git
- Docker (optional)
- Groq API key
- LangSmith API key (optional, for tracing)

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd RAG_with_eval_harness
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Alternatively, use `uv`:

```bash
uv pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
# LLM Provider
GROQ_API_KEY=your_groq_api_key

# LangSmith Observability
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=RAG-Policy-Eval-Harness
```

Never commit your `.env` file or expose API keys in the repository.

### 5. Run the Application

```bash
uvicorn app:app --reload --port 8000
```

## 🐳 Docker Deployment

Build the Docker image:

```bash
docker build -t rag-eval-app .
```

Run the container:

```bash
docker run -d \
  --name rag-chat-server \
  -p 8000:8000 \
  --env-file .env \
  -v "${PWD}/chroma_db:/app/chroma_db" \
  -v "${PWD}/rag_feedback.db:/app/rag_feedback.db" \
  rag-eval-app
```

The mounted volumes preserve the ChromaDB data and SQLite database outside the container.

## 🌐 API Endpoints and Interfaces

After starting the application, the following interfaces are available:

| Endpoint | Method | Purpose |
|---|---|---|
| `/docs` | GET | Interactive Swagger API documentation |
| `/api/chat` | POST | Submit a company-policy question |
| `/api/feedback` | POST | Submit feedback about an answer |
| `/admin` | GET | Access the administrative control center |

### Chat API

`POST /api/chat`

Supports configurable retrieval strategies:

- `hybrid`
- `dense`
- `bm25`
- `hyde`

The request can also specify `top_k` to control the number of retrieved results.

See the interactive Swagger documentation for the exact request and response schemas.

### Feedback API

`POST /api/feedback`

Records user feedback, including positive and negative ratings and optional comments.

## 🔮 Future Improvements

The following features are planned improvements, not claims about currently implemented functionality.

- **Semantic caching:** Use Redis to cache repeated policy queries.
- **Cross-encoder reranking:** Rerank hybrid retrieval results before generation.
- **Automated evaluation gates:** Run evaluation tests in CI/CD and detect quality regressions.
- **Document versioning:** Track policy updates and maintain document history.
- **Incremental ingestion:** Process only changed documents.
- **Role-based access control:** Restrict policy retrieval based on employee permissions.
- **Advanced monitoring:** Add more detailed latency, error, and quality dashboards.

## 🎯 Project Objective

The main objective is to explore how an enterprise-oriented RAG system can be designed, evaluated, monitored, and improved under practical hardware and engineering constraints.

Rather than relying on a single retrieval technique or an unmeasured prompt configuration, this project emphasizes:

- Modular architecture.
- Measurable retrieval quality.
- Controlled query routing.
- Grounded answer generation.
- Observability and debugging.
- Resource-aware engineering.

**The focus is not just making RAG work, but understanding how to make it reliable and measurable.** 