## Retrival eval logs

(RAG_with_eval_harness) PS E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness> python -m evaluation.retrival.run_eval
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1951.81it/s]
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'sparse' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 5/5 | Supported: True
[2/5] Querying & Evaluating GD-02...
   -> Score: 5/5 | Supported: True
[3/5] Querying & Evaluating GD-03...
   -> Score: 1/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\BM25\eval_results_hybrid_k3.html

========================================
RETRIEVAL EVAL SUMMARY (sparse | top_k=3)
========================================
Total Queries : 5
Average Score : 4.20 / 5.00
Pass Rate     : 80.0%
Saved Report  : evaluation/retrival/BM25/eval_results_hybrid_k3.json
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 2176.65it/s]
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'hyde' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 1/5 | Supported: False
[2/5] Querying & Evaluating GD-02...
   -> Score: 1/5 | Supported: False
[3/5] Querying & Evaluating GD-03...
   -> Score: 2/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\HyDE\eval_results_hybrid_k3.html

========================================
RETRIEVAL EVAL SUMMARY (hyde | top_k=3)
========================================
Total Queries : 5
Average Score : 2.80 / 5.00
Pass Rate     : 40.0%
Saved Report  : evaluation/retrival/HyDE/eval_results_hybrid_k3.json
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1965.51it/s]
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'hybrid' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 5/5 | Supported: True
[2/5] Querying & Evaluating GD-02...
   -> Score: 5/5 | Supported: True
[3/5] Querying & Evaluating GD-03...
   -> Score: 1/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\Hybrid\eval_results_hybrid_k3.html

========================================
RETRIEVAL EVAL SUMMARY (hybrid | top_k=3)
========================================
Total Queries : 5
Average Score : 4.20 / 5.00
Pass Rate     : 80.0%
Saved Report  : evaluation/retrival/Hybrid/eval_results_hybrid_k3.json
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1830.95it/s]
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'mmr' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 5/5 | Supported: True
[2/5] Querying & Evaluating GD-02...
   -> Score: 5/5 | Supported: True
[3/5] Querying & Evaluating GD-03...
   -> Score: 1/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\MMR\eval_results_hybrid_k3.html

========================================
RETRIEVAL EVAL SUMMARY (mmr | top_k=3)
========================================
Total Queries : 5
Average Score : 4.20 / 5.00
Pass Rate     : 80.0%
Saved Report  : evaluation/retrival/MMR/eval_results_hybrid_k3.json
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1911.50it/s]
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'multi_query' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 5/5 | Supported: True
[2/5] Querying & Evaluating GD-02...
   -> Score: 5/5 | Supported: True
[3/5] Querying & Evaluating GD-03...
   -> Score: 1/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\Multi_Query\eval_results_hybrid_k3.html

========================================
RETRIEVAL EVAL SUMMARY (multi_query | top_k=3)
========================================
Total Queries : 5
Average Score : 4.20 / 5.00
Pass Rate     : 80.0%
Saved Report  : evaluation/retrival/Multi_Query/eval_results_hybrid_k3.json
Initializing VectorDB & Hybrid Retriever...
Loading weights: 100%|████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1373.22it/s]
E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness\src\ingestion\chroma_store.py:33: FutureWarning: The `get_sentence_embedding_dimension` method has been renamed to `get_embedding_dimension`.
  self.vector_size = self.embedder.get_sentence_embedding_dimension()
Loaded 5 golden queries. Running 'dense' retrieval (top_k=3)...

[1/5] Querying & Evaluating GD-01...
   -> Score: 1/5 | Supported: False
[2/5] Querying & Evaluating GD-02...
   -> Score: 1/5 | Supported: False
[3/5] Querying & Evaluating GD-03...
   -> Score: 1/5 | Supported: False
[4/5] Querying & Evaluating GD-04...
   -> Score: 5/5 | Supported: True
[5/5] Querying & Evaluating GD-05...
   -> Score: 5/5 | Supported: True
Saved HTML    : evaluation\retrival\Semantic\eval_results_dense_k3.html

========================================
RETRIEVAL EVAL SUMMARY (dense | top_k=3)
========================================
Total Queries : 5
Average Score : 2.60 / 5.00
Pass Rate     : 40.0%
Saved Report  : evaluation/retrival/Semantic/eval_results_dense_k3.json
----------- Compliterd all -----------
(RAG_with_eval_harness) PS E:\Z_RAG_EVAL_Harness\RAG_with_eval_harness> 