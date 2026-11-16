from evaluation.retrival.retrieval_evaluator import run_evaluation_pipeline

def _main():
    run_evaluation_pipeline(
        golden_path=r"eval_dataset\test_gold.json",
        output_path="evaluation/retrival/BM25/eval_results_hybrid_k3.json",
        strategy="sparse",
        top_k=3
    )


