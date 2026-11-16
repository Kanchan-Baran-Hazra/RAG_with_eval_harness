from evaluation.retrival.BM25.runner import _main as bm25_main
from evaluation.retrival.HyDE.runner import _main as hyde_main
from evaluation.retrival.Hybrid.runner import _main as hybrid_main
from evaluation.retrival.MMR.runner import _main as mmr_main
from evaluation.retrival.Multi_Query.runner import _main as multi_quary_main
from evaluation.retrival.Semantic.runner import _main as symantic_main


def run_eval():
    bm25_main()
    hyde_main()
    hybrid_main()
    mmr_main()
    multi_quary_main()
    symantic_main()
    print("----------- Compliterd all -----------")

if __name__ == "__main__":
    run_eval()