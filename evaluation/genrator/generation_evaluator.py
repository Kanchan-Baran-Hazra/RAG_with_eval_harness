import json
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel, Field

# Import your retriever & your RAG answer generator (adjust import paths)
from src.ingestion.chroma_store import VectorDBManager
from src.retrival.rag_retriever import RAGRetriever
from src.genrator.rag_generator import generate_rag_answer  # Your RAG generation function

load_dotenv()

# 1. Multi-Metric Structured Output Schema (All 3 Generation Dimensions in 1 Call)
class GenerationEvalResult(BaseModel):
    # Dimension 1: Faithfulness (Groundedness / Hallucination Check)
    faithfulness_score: int = Field(
        ..., description="1-5 score. 5 = strictly derived from context; 1 = severe hallucinations."
    )
    is_faithful: bool = Field(
        ..., description="True if every claim in generated answer is supported by retrieved context."
    )
    hallucinated_claims: list[str] = Field(
        default_factory=list, description="Claims in generated answer not found in context."
    )

    # Dimension 2: Answer Correctness (Factual alignment with Ground Truth)
    correctness_score: int = Field(
        ..., description="1-5 score. 5 = matches ground truth facts completely; 1 = completely wrong."
    )
    is_correct: bool = Field(
        ..., description="True if generated answer accurately captures core facts of ground truth."
    )

    # Dimension 3: Answer Relevance (Directly addresses user query without fluff)
    relevance_score: int = Field(
        ..., description="1-5 score. 5 = directly and concisely answers the question; 1 = off-topic."
    )

    reason: str = Field(..., description="Brief 1-2 sentence explanation covering all 3 scores.")


# 2. Rate-Limited Judge Setup (1 req / 12s for Groq 8K TPM safety)
rate_limiter = InMemoryRateLimiter(
    requests_per_second=1 / 12,
    check_every_n_seconds=0.5,
    max_bucket_size=1
)

judge_llm = init_chat_model(
    "groq:openai/gpt-oss-120b",
    temperature=0.0,
    rate_limiter=rate_limiter,
)

# Apply structured output FIRST, retry wrapper LAST
structured_judge = judge_llm.with_structured_output(GenerationEvalResult).with_retry(
    stop_after_attempt=5,
    wait_exponential_jitter=True
)

# 3. Multi-Dimensional Generation Judge Prompt
gen_eval_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an impartial RAG Generation Judge. Grade the 'Generated Answer' across 3 dimensions:\n"
        "1. Faithfulness: Every claim must come ONLY from 'Retrieved Context'. Flag outside facts as hallucinations.\n"
        "2. Correctness: Compare 'Generated Answer' against 'Ground Truth' for factual accuracy.\n"
        "3. Relevance: Check if 'Generated Answer' directly answers the 'Question'."
    )),
    ("human", (
        "Question:\n{question}\n\n"
        "Ground Truth:\n{ground_truth}\n\n"
        "Retrieved Context:\n{retrieved_context}\n\n"
        "Generated Answer:\n{generated_answer}"
    ))
])

gen_eval_chain = gen_eval_prompt | structured_judge


def evaluate_generation(
    question: str,
    ground_truth: str,
    retrieved_context: str,
    generated_answer: str
) -> GenerationEvalResult:
    return gen_eval_chain.invoke({
        "question": question,
        "ground_truth": ground_truth,
        "retrieved_context": retrieved_context,
        "generated_answer": generated_answer
    })


def format_hits(hits: list[dict]) -> str:
    if not hits:
        return "NO CONTEXT RETRIEVED."
    return "\n\n---\n\n".join(
        f"[Chunk {i}]\n{hit['text']}" for i, hit in enumerate(hits, start=1)
    )


# 4. Standalone Generation Evaluation Pipeline
def run_generation_eval_pipeline(
    golden_path: str,
    output_path: str,
    strategy: str = "hybrid",
    top_k: int = 3
):
    print("Initializing Retriever & Generator Pipeline...")
    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db)

    data = json.loads(Path(golden_path).read_text(encoding="utf-8"))
    results_log = []

    print(f"Loaded {len(data)} golden queries. Evaluating RAG Generation...\n")

    for idx, item in enumerate(data, start=1):
        item_id = item.get("id", f"q_{idx}")
        query = item.get("question") or item.get("query")
        ground_truth = item["ground_truth"]

        print(f"[{idx}/{len(data)}] Generating & Evaluating {item_id}...")

        # Step A: Retrieve Context
        hits = retriever.retrieve(query, strategy=strategy, top_k=top_k)
        formatted_context = format_hits(hits)

        # Step B: Run Your RAG Generator (Replace with your actual generator call)
        # Note: If your generator also uses Groq, rate_limiter ensures safe pacing
        generated_answer = generate_rag_answer(query=query, context_chunks=hits)

        # Step C: Grade Generation across Faithfulness, Correctness & Relevance
        eval_res = evaluate_generation(
            question=query,
            ground_truth=ground_truth,
            retrieved_context=formatted_context,
            generated_answer=generated_answer
        )

        record = {
            "id": item_id,
            "question": query,
            "ground_truth": ground_truth,
            "generated_answer": generated_answer,
            "retrieved_hits": hits,
            "evaluation": eval_res.model_dump()
        }
        results_log.append(record)

        print(
            f"   -> Faithful: {eval_res.faithfulness_score}/5 ({eval_res.is_faithful}) | "
            f"Correct: {eval_res.correctness_score}/5 ({eval_res.is_correct}) | "
            f"Relevant: {eval_res.relevance_score}/5"
        )
        if eval_res.hallucinated_claims:
            print(f"   -> Hallucinations: {eval_res.hallucinated_claims}")

    # Save JSON Report
    Path(output_path).write_text(json.dumps(results_log, indent=2), encoding="utf-8")

    # Summary Dashboard
    total = len(results_log)
    if total:
        avg_faith = sum(r["evaluation"]["faithfulness_score"] for r in results_log) / total
        avg_corr = sum(r["evaluation"]["correctness_score"] for r in results_log) / total
        avg_rel = sum(r["evaluation"]["relevance_score"] for r in results_log) / total
        faithful_rate = sum(1 for r in results_log if r["evaluation"]["is_faithful"]) / total * 100
        correct_rate = sum(1 for r in results_log if r["evaluation"]["is_correct"]) / total * 100

        print("\n" + "=" * 50)
        print("GENERATION EVAL SUMMARY")
        print("=" * 50)
        print(f"Total Queries      : {total}")
        print(f"Avg Faithfulness   : {avg_faith:.2f}/5.00 (Pass: {faithful_rate:.1f}%)")
        print(f"Avg Correctness    : {avg_corr:.2f}/5.00 (Pass: {correct_rate:.1f}%)")
        print(f"Avg Relevance      : {avg_rel:.2f}/5.00")
        print(f"Saved Report       : {output_path}")


if __name__ == "__main__":
    run_generation_eval_pipeline(
        golden_path="golden.json",
        output_path="gen_eval_results.json",
        strategy="hybrid",
        top_k=3
    )