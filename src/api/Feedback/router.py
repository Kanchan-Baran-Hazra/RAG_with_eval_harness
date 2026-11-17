# Add these imports to your existing app.py imports
from pydantic import Field,BaseModel
from typing import Optional
from fastapi import HTTPException,APIRouter
from src.api.db.main import SessionLocal
from src.api.Feedback.models import FeedbackRecord


# --- New Feedback Pydantic Schemas ---
class FeedbackRequest(BaseModel):
    query: str = Field(..., description="The user's original question.")
    answer: str = Field(..., description="The LLM's generated answer.")
    rating: str = Field(..., description="Rating: 'thumbs_up' or 'thumbs_down'.")
    comment: Optional[str] = Field(None, description="Optional user feedback comments.")
    strategy: Optional[str] = Field("hybrid", description="Retrieval strategy used.")

class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int
    message: str


feed_router = APIRouter()


# {
#   "query": "What is the monetary gift cap?",
#   "answer": "The monetary gift cap is $50.",
#   "rating": "thumbs_up",
#   "comment": "Very accurate and quick answer!",
#   "strategy": "hybrid"
# }


# --- New API Endpoint for Feedback ---
@feed_router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(payload: FeedbackRequest):
    try:
        session = SessionLocal()
        
        db_feedback = FeedbackRecord(
            query=payload.query,
            answer=payload.answer,
            rating=payload.rating,
            comment=payload.comment,
            strategy=payload.strategy
        )
        
        session.add(db_feedback)
        session.commit()
        session.refresh(db_feedback)
        session.close()

        return FeedbackResponse(
            status="success",
            feedback_id=db_feedback.id,
            message="Thank you! Your feedback has been recorded."
        )

    except Exception as e:
        print(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))