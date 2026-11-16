import json
import os
from deepeval import evaluate
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
)
from deepeval.evaluate import AsyncConfig
from src.retrival.rag_retriever import RAGRetriever
from src.LLM.litellm_client import LiteLLMClient
from src.ingestion.chroma_store import VectorDBManager


import time
import asyncio
import litellm
from deepeval.models import DeepEvalBaseLLM

class LiteLLMJudge(DeepEvalBaseLLM):
    def __init__(self, llm_client: LiteLLMClient):
        self.llm = llm_client

    def load_model(self):
        return self.llm

    def generate(self, prompt: str) -> str:
        # Pace every individual LLM call (~10s gap keeps you under 8,000 TPM)
        time.sleep(10)
        for attempt in range(5):
            try:
                return self.llm.generate(prompt)
            except litellm.RateLimitError:
                wait_time = 15 * (attempt + 1)
                print(f"Groq TPM limit hit. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        return self.llm.generate(prompt)

    async def a_generate(self, prompt: str) -> str:
        return await asyncio.to_thread(self.generate, prompt)

    def get_model_name(self) -> str:
        return self.llm.model


# 1. Load your golden dataset JSON
with open("eval_dataset\golden.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# 2. Build a list of LLMTestCase objects by running your retriever on each query
test_cases = []
db = VectorDBManager(backend="chroma", collection_name="rag_policies")
retriever = RAGRetriever(vector_db=db)

for item in dataset[:2]:
    # Skip unanswerable_negative queries for contextual precision/recall
    if item.get("query_type") == "unanswerable_negative" or not item.get("source_documents"):
        continue

    query = item["question"]
    expected_answer = item["ground_truth"]

    # Fetch real chunks from your RAGRetriever
    retrieved_chunks = retriever.retrieve(query, strategy="hybrid", top_k=5)
    retrieved_texts = [chunk["text"] for chunk in retrieved_chunks]

    test_cases.append(
        LLMTestCase(
            input=query,
            expected_output=expected_answer,
            retrieval_context=retrieved_texts,
        )
    )

print(f"Built {len(test_cases)} retriever test cases.")


# Initialize Gemini Judge via your LiteLLM wrapper
judge = LiteLLMJudge(LiteLLMClient(model="groq/openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY")))

# 3. Initialize DeepEval Retriever Metrics
retriever_metrics = [
    ContextualPrecisionMetric(threshold=0.7, model=judge, include_reason=True),
    ContextualRecallMetric(threshold=0.7, model=judge, include_reason=True),
    ContextualRelevancyMetric(threshold=0.7, model=judge, include_reason=True),
]

# 4. Run batch evaluation (max_concurrent=2 prevents Gemini API rate-limit errors)
results = evaluate(
    test_cases=test_cases,
    metrics=retriever_metrics,
    async_config=AsyncConfig(max_concurrent=1, throttle_value=5.0),
)

print(results)














# from typing import Any, Dict, List


# def evaluate_retriever_deterministic(
#     test_queries: List[Dict[str, Any]], retriever, top_k: int = 5
# ) -> Dict[str, float]:
#     """
#     Evaluates retriever performance against a ground truth dataset of expected source files.

#     test_queries format:
#     [
#         {
#             "query": "What is the annual leave policy?",
#             "expected_source": "03_Annual_Leave_Policy.pdf"
#         },
#         ...
#     ]
#     """
#     hits = 0
#     mrr_sum = 0.0
#     total = len(test_queries)

#     for item in test_queries:
#         query = item["question"]
#         expected_source = item["source_documents"]

#         # Skip unanswerable negative queries for retrieval Hit Rate/MRR
#         if not expected_source:
#             continue

#         # Run your retriever
#         retrieved_chunks = retriever.retrieve(query, strategy="hybrid", top_k=top_k)

#         # Check if expected source is in retrieved results and find its rank
#         found_rank = None
#         for rank, chunk in enumerate(retrieved_chunks, start=1):
#             source = chunk.get("metadata", {}).get("source_file")
#             # print(f"Source: {source} === Expected: {expected_source}")

#             # Handle both list of expected files or a single string
#             is_match = (
#                 source in expected_source
#                 if isinstance(expected_source, list)
#                 else source == expected_source
#             )
#             if is_match:
#                 found_rank = rank
#                 break

#         if found_rank is not None:
#             hits += 1
#             mrr_sum += 1.0 / found_rank

#     return {
#         "Hit Rate @ K": round(hits / total, 4) if total > 0 else 0.0,
#         "MRR (Mean Reciprocal Rank)": round(mrr_sum / total, 4) if total > 0 else 0.0,
#         "Total Queries Evaluated": total,
#     }


# if __name__ == "__main__":
#     import os
#     import json
#     from src.retrival.rag_retriever import RAGRetriever
#     from src.ingestion.chroma_store import VectorDBManager
#     DATASET_PATH = "eval_dataset\golden.json"  # Path to your test queries JSON file
#     with open(DATASET_PATH, "r") as f:
#         test_queries = json.load(f)


#     evaluation_results = evaluate_retriever_deterministic(
#         test_queries=test_queries,
#         retriever=RAGRetriever(VectorDBManager(backend="chroma", collection_name="rag_policies")),
#         top_k=5,
#     )

#     print("Retriever Evaluation Results:")
#     for metric, value in evaluation_results.items():
#         print(f"{metric}: {value}")

















# from deepeval import evaluate
# from deepeval.models import DeepEvalBaseLLM
# from deepeval.test_case import LLMTestCase
# from deepeval.metrics import (
#     AnswerRelevancyMetric,
#     FaithfulnessMetric,
#     ContextualPrecisionMetric,
#     ContextualRecallMetric,
#     ContextualRelevancyMetric,
# )
# import os
# from src.LLM.litellm_client import LiteLLMClient


# # 1. Wrap your LiteLLMClient as DeepEval's Judge Model
# class LiteLLMJudge(DeepEvalBaseLLM):
#     def __init__(self, llm_client: LiteLLMClient):
#         self.llm = llm_client

#     def load_model(self):
#         return self.llm

#     def generate(self, prompt: str) -> str:
#         return self.llm.generate(prompt)

#     async def a_generate(self, prompt: str) -> str:
#         return self.llm.generate(prompt)

#     def get_model_name(self) -> str:
#         return self.llm.model


# # Initialize Gemini Judge via your LiteLLM wrapper
# judge = LiteLLMJudge(LiteLLMClient(model="groq/openai/gpt-oss-20b",api_key=os.getenv("GROQ_API_KEY")))

# # 2. Create a single RAG Test Case (simulating outputs from your Retriever & Generator)
# test_case = LLMTestCase(
#     input="How many days of paid annual leave do full-time employees get?",
#     actual_output="Full-time employees receive 20 days of paid annual leave per calendar year.",
#     expected_output="Full-time staff are entitled to 20 paid annual leave days annually.",
#     retrieval_context=[
#         "Section 2.1: Full-time employees receive 20 days of paid annual leave per calendar year.",
#         "Section 4.3: Office cafeteria hours are from 8:30 AM to 6:00 PM on weekdays.",  # Intentional noise chunk
#     ],
# )

# # 3. Initialize DeepEval's 5 Core RAG Metrics
# metrics = [
#     # Generator Metrics
#     FaithfulnessMetric(threshold=0.7, model=judge, include_reason=True),
#     AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True),
#     # Retriever Metrics
#     ContextualPrecisionMetric(threshold=0.7, model=judge, include_reason=True),
#     ContextualRecallMetric(threshold=0.7, model=judge, include_reason=True),
#     ContextualRelevancyMetric(threshold=0.7, model=judge, include_reason=True),
# ]

# # 4. Run Evaluation
# results = evaluate(test_cases=[test_case], metrics=metrics)