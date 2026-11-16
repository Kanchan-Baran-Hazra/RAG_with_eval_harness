from evaluation.retrival.retrieval_evaluator import run_evaluation_pipeline

def _main():
    run_evaluation_pipeline(
        golden_path=r"eval_dataset\test_gold.json",
        output_path="evaluation/retrival/Multi_Query/eval_results_hybrid_k3.json",
        strategy="multi_query",
        top_k=3
    )


