from contextlib import asynccontextmanager
from typing import Any, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.ingestion.chroma_store import VectorDBManager
from src.retrival.rag_retriever import RAGRetriever
from src.workflow import build_rag_workflow

from src.api.db.main import init_db

from src.api.Feedback.router import feed_router

load_dotenv()

db: Optional[VectorDBManager] = None
rag_workflow: Optional[Any] = None


@asynccontextmanager
async def startup_event(app: FastAPI):
    global db, rag_workflow
    print("Initializing VectorDB, Retriever, and LangGraph Workflow...")
    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db)
    rag_workflow = build_rag_workflow(retriever=retriever)
    init_db()
    print("RAG LangGraph Workflow initialized successfully!")
    yield
    print("Shutting down RAG Chat API...")


app = FastAPI(
    title="RAG Chat API",
    description="API for hybrid RAG retrieval, HyDE generation, and LangGraph routing.",
    version="1.0.0",
    lifespan=startup_event
)

app.include_router(feed_router, prefix="/api", tags=["Feedback"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Response Schemas ---
class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's question.", example="What is the monetary gift cap?")
    strategy: str = Field("hybrid", description="Retrieval strategy: hybrid, dense, bm25, or hyde.")
    top_k: int = Field(3, description="Number of context chunks to retrieve.", ge=1, le=10)


class SourceChunk(BaseModel):
    text: str
    score: float
    metadata: dict


class ChatResponse(BaseModel):
    query: str
    route: str
    answer: str
    sources: List[str] = []
    strategy: str
    retrieved_chunks: List[SourceChunk]


# --- API Endpoints ---
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "RAG Chat API"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    try:
        if not rag_workflow:
            raise HTTPException(status_code=500, detail="Workflow not initialized.")

        # Execute the LangGraph workflow
        final_state = rag_workflow.invoke({
            "query": payload.query,
            "strategy": payload.strategy,
            "top_k": payload.top_k,
        })

        formatted_chunks = [
            SourceChunk(
                text=hit.get("text", ""),
                score=hit.get("score", 0.0),
                metadata=hit.get("metadata", {})
            )
            for hit in final_state.get("retrieved_hits", [])
        ]

        return ChatResponse(
            query=payload.query,
            route=final_state.get("route", "unknown"),
            answer=final_state.get("answer", ""),
            sources=final_state.get("sources", []),
            strategy=payload.strategy,
            retrieved_chunks=formatted_chunks
        )

    except Exception as e:
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))





























# import os
# from typing import List, Optional
# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# # Import your custom RAG modules (adjust import paths if needed)
# from src.ingestion.chroma_store import VectorDBManager
# from src.retrival.rag_retriever import RAGRetriever
# from src.pipeline import _run  # Replace with your actual generator function
# from contextlib import asynccontextmanager

# load_dotenv()

# @asynccontextmanager
# async def startup_event(app:FastAPI):
#     global db, retriever
#     print("Initializing VectorDB and RAG Retriever...")
#     db = VectorDBManager(backend="chroma", collection_name="rag_policies")
#     retriever = RAGRetriever(vector_db=db)
#     print("RAG Pipeline initialized successfully!")
#     yield  # Application runs while yielded

#     # --- Shutdown logic (optional cleanup when server stops) ---
#     print("Shutting down RAG Chat API...")


# # Initialize FastAPI app
# app = FastAPI(
#     title="RAG Chat API",
#     description="API for hybrid RAG retrieval, HyDE generation, and conversational QA.",
#     version="1.0.0",
#     lifespan=startup_event  # Use the async context manager for startup/shutdown
# )

# # Enable CORS (so a frontend like React/Next.js or Streamlit can talk to it)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Set to specific frontend origins in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Global instances (initialized once on startup to avoid reloading models/DBs per request)
# db: Optional[VectorDBManager] = None
# retriever: Optional[RAGRetriever] = None


# # --- Request & Response Schemas ---
# class ChatRequest(BaseModel):
#     query: str = Field(..., description="The user's question.", example="What is the monetary gift cap?")
#     strategy: str = Field("hybrid", description="Retrieval strategy: hybrid, dense, bm25, or hyde.")
#     top_k: int = Field(3, description="Number of context chunks to retrieve.", ge=1, le=10)


# class SourceChunk(BaseModel):
#     text: str
#     score: float
#     metadata: dict


# class ChatResponse(BaseModel):
#     query: str
#     answer: str
#     strategy: str
#     retrieved_chunks: List[SourceChunk]


# # --- API Endpoints ---
# @app.get("/")
# def health_check():
#     return {"status": "healthy", "service": "RAG Chat API"}


# @app.post("/api/chat", response_model=ChatResponse)
# def chat_endpoint(payload: ChatRequest):
#     try:
#         if not retriever:
#             raise HTTPException(status_code=500, detail="Retriever not initialized.")

#         # 1. Retrieve relevant chunks using the specified strategy
#         hits = retriever.retrieve(payload.query, strategy=payload.strategy, top_k=payload.top_k)

#         # 2. Generate RAG answer using retrieved chunks
#         # (Passes the hit list to your generator)
#         answer = _run(query=payload.query, context_chunks=hits)

#         # 3. Format response
#         formatted_chunks = [
#             SourceChunk(
#                 text=hit.get("text", ""),
#                 score=hit.get("score", 0.0),
#                 metadata=hit.get("metadata", {})
#             )
#             for hit in hits
#         ]

#         return ChatResponse(
#             query=payload.query,
#             answer=answer.get("answer", ""),
#             strategy=payload.strategy,
#             retrieved_chunks=formatted_chunks
#         )

#     except Exception as e:
#         print(f"Error handling chat request: {e}")
#         raise HTTPException(status_code=500, detail=str(e))









































# import os
# from typing import List, Optional
# from dotenv import load_dotenv
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# # Import your custom RAG modules (adjust import paths if needed)
# from src.pipeline import _run

# load_dotenv()

# # Initialize FastAPI app
# app = FastAPI(
#     title="RAG Chat API",
#     description="API for hybrid RAG retrieval, HyDE generation, and conversational QA.",
#     version="1.0.0"
# )

# # Enable CORS (so a frontend like React/Next.js or Streamlit can talk to it)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Set to specific frontend origins in production
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # --- Request & Response Schemas ---
# class ChatRequest(BaseModel):
#     query: str = Field(..., description="The user's question.", example="What is the monetary gift cap?")
#     # strategy: str = Field("hybrid", description="Retrieval strategy: hybrid, dense, bm25, or hyde.")
#     # top_k: int = Field(3, description="Number of context chunks to retrieve.", ge=1, le=10)


# class SourceChunk(BaseModel):
#     text: str
#     score: float
#     metadata: dict


# class ChatResponse(BaseModel):
#     query: str
#     answer: str
#     # strategy: str
#     # retrieved_chunks: List[SourceChunk]


# # --- API Endpoints ---
# @app.get("/")
# def health_check():
#     return {"status": "healthy", "service": "RAG Chat API"}


# @app.post("/api/chat", response_model=ChatResponse)
# def chat_endpoint(payload: ChatRequest):
#     try:
#         # if not retriever:
#         #     raise HTTPException(status_code=500, detail="Retriever not initialized.")

#         # # 1. Retrieve relevant chunks
#         # hits = retriever.retrieve(payload.query, strategy=payload.strategy, top_k=payload.top_k)

#         # 2. Generate RAG answer
#         raw_result = _run(query=payload.query)
#         print(type(raw_result))

#         # Handle dict return from generate_rag_answer vs plain str
#         if isinstance(raw_result, dict):
#             answer_text = raw_result.get("answer")
#         else:
#             answer_text = raw_result.get("answer")

#         # 3. Format response
#         # formatted_chunks = [
#         #     SourceChunk(
#         #         text=hit.get("text", ""),
#         #         score=hit.get("score", 0.0),
#         #         metadata=hit.get("metadata", {})
#         #     )
#         #     for hit in hits
#         # ]

#         return ChatResponse(
#             query=payload.query,
#             answer=answer_text,
#             # strategy=payload.strategy,
#             # retrieved_chunks=formatted_chunks
#         )

#     except Exception as e:
#         print(f"Error handling chat request: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

#     except Exception as e:
#         print(f"Error handling chat request: {e}")
#         raise HTTPException(status_code=500, detail=str(e))