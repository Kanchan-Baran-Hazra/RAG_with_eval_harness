import os
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import your custom RAG modules (adjust import paths if needed)
from src.ingestion.chroma_store import VectorDBManager
from src.retrival.rag_retriever import RAGRetriever
from src.pipeline import _run  # Replace with your actual generator function
from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def startup_event(app:FastAPI):
    global db, retriever
    print("Initializing VectorDB and RAG Retriever...")
    db = VectorDBManager(backend="chroma", collection_name="rag_policies")
    retriever = RAGRetriever(vector_db=db)
    print("RAG Pipeline initialized successfully!")
    yield  # Application runs while yielded

    # --- Shutdown logic (optional cleanup when server stops) ---
    print("Shutting down RAG Chat API...")


# Initialize FastAPI app
app = FastAPI(
    title="RAG Chat API",
    description="API for hybrid RAG retrieval, HyDE generation, and conversational QA.",
    version="1.0.0",
    lifespan=startup_event  # Use the async context manager for startup/shutdown
)

# Enable CORS (so a frontend like React/Next.js or Streamlit can talk to it)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific frontend origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (initialized once on startup to avoid reloading models/DBs per request)
db: Optional[VectorDBManager] = None
retriever: Optional[RAGRetriever] = None


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
    answer: str
    strategy: str
    retrieved_chunks: List[SourceChunk]


# --- API Endpoints ---
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "RAG Chat API"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    try:
        if not retriever:
            raise HTTPException(status_code=500, detail="Retriever not initialized.")

        # 1. Retrieve relevant chunks using the specified strategy
        hits = retriever.retrieve(payload.query, strategy=payload.strategy, top_k=payload.top_k)

        # 2. Generate RAG answer using retrieved chunks
        # (Passes the hit list to your generator)
        answer = _run(query=payload.query, context_chunks=hits)

        # 3. Format response
        formatted_chunks = [
            SourceChunk(
                text=hit.get("text", ""),
                score=hit.get("score", 0.0),
                metadata=hit.get("metadata", {})
            )
            for hit in hits
        ]

        return ChatResponse(
            query=payload.query,
            answer=answer.get("answer", ""),
            strategy=payload.strategy,
            retrieved_chunks=formatted_chunks
        )

    except Exception as e:
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e))