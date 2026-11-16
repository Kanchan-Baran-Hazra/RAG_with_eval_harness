import json
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel, Field
from src.ingestion.chroma_store import VectorDBManager
from src.retrival.rag_retriever import RAGRetriever
from evaluation.retrival.html_reporter import generate_html_report

load_dotenv()

# 1. Schema
class EvaluationResult(BaseModel):
    score: int = Field(..., description="1 to 5 score.")
    is_supported: bool = Field(..., description="True if ground truth facts are in context.")
    # missing_facts: list[str] = Field(default_factory=list, description="Missing facts from ground truth.")
    reason: str = Field(..., description="Brief 1-sentence justification.")

# 2. Rate-Limited Model Setup (1 req / 12s for 8K TPM safety)
rate_limiter = InMemoryRateLimiter(
    requests_per_second=1 / 12,
    check_every_n_seconds=0.5,
    max_bucket_size=1
)

llm = init_chat_model(
    "groq:openai/gpt-oss-120b",
    temperature=0.0,
    rate_limiter=rate_limiter,
)

structured_llm = llm.with_structured_output(EvaluationResult).with_retry(
    stop_after_attempt=5,
    wait_exponential_jitter=True
)

# 3. Chain
eval_prompt = ChatPromptTemplate.from_messages([
    ("system", "Grade if Retrieved Context covers Ground Truth. Strictly use provided text."),
    ("human", "Ground Truth:\n{ground_truth}\n\nRetrieved Context:\n{retrieved_context}")
])

eval_chain = eval_prompt | structured_llm

def evaluate_retrieval(ground_truth: str, retrieved_context: str) -> EvaluationResult:
    return eval_chain.invoke({
        "ground_truth": ground_truth,
        "retrieved_context": retrieved_context
    })

def format_hits(hits: list[dict]) -> str:
    """Formats hybrid retriever hits into a clean text block for the LLM judge."""
    if not hits:
        return "NO CONTEXT RETRIEVED."
    
    formatted_chunks = []
    for i, hit in enumerate(hits, start=1):
        # Include rank and RRF/hybrid score for clear context separation
        formatted_chunks.append(f"[Chunk {i} | Score: {hit['score']}]\n{hit['text']}")
    
    return "\n\n---\n\n".join(formatted_chunks)

# 4. End-to-End Live Retrieval & Evaluation Runner
def run_evaluation_pipeline(
    golden_path: str, 
    output_path: str, 
    strategy: str = "hybrid", 
    top_k: int = 3
):
    # Initialize your VectorDB and Retriever ONCE before the loop
    print("Initializing VectorDB & Hybrid Retriever...")
    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db)

    # Load golden dataset
    data = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    results_log = []

    print(f"Loaded {len(data)} golden queries. Running '{strategy}' retrieval (top_k={top_k})...\n")

    for idx, item in enumerate(data, start=1):
        item_id = item.get("id", f"q_{idx}")
        # Support common key names ("question" or "query")
        query = item.get("question") or item.get("query")
        ground_truth = item["ground_truth"]

        print(f"[{idx}/{len(data)}] Querying & Evaluating {item_id}...")

        # Step A: Live Retrieval from Chroma
        hits = retriever.retrieve(query, strategy=strategy, top_k=top_k)
        formatted_context = format_hits(hits)

        # Step B: LLM Judge Evaluation (auto-paced at 12s/req)
        eval_res = evaluate_retrieval(
            ground_truth=ground_truth,
            retrieved_context=formatted_context
        )

        # Step C: Log both retrieved chunks (with metadata/scores) and judge verdict
        record = {
            "id": item_id,
            "question": query,
            "ground_truth": ground_truth,
            "retrieval_config": {"strategy": strategy, "top_k": top_k},
            "retrieved_hits": hits,  # Saved for debugging bad retrievals!
            "evaluation": eval_res.model_dump()
        }
        results_log.append(record)
        
        print(f"   -> Score: {eval_res.score}/5 | Supported: {eval_res.is_supported}")
        # if eval_res.missing_facts:
        #     print(f"   -> Missing: {eval_res.missing_facts}")

    # Save complete diagnostic report
    Path(output_path).write_text(json.dumps(results_log, indent=2), encoding="utf-8")

    html_path = str(Path(output_path).with_suffix(".html"))
    generate_html_report(results_log, html_path)
    print(f"Saved HTML    : {html_path}")

    # Summary Metrics
    total = len(results_log)
    avg_score = sum(r["evaluation"]["score"] for r in results_log) / total if total else 0
    pass_rate = sum(1 for r in results_log if r["evaluation"]["is_supported"]) / total * 100 if total else 0

    print("\n" + "=" * 40)
    print(f"RETRIEVAL EVAL SUMMARY ({strategy} | top_k={top_k})")
    print("=" * 40)
    print(f"Total Queries : {total}")
    print(f"Average Score : {avg_score:.2f} / 5.00")
    print(f"Pass Rate     : {pass_rate:.1f}%")
    print(f"Saved Report  : {output_path}")

if __name__ == "__main__":
    run_evaluation_pipeline(
        golden_path=r"eval_dataset\test_gold.json",
        output_path="evaluation/retrival/eval_results_hybrid_k3.json",
        strategy="hybrid",
        top_k=3
    )






