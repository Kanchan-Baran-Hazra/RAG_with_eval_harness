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