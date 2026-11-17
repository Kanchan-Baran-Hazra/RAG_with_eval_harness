from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.api.db.main import Base

class FeedbackRecord(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(String(20), nullable=False)  # "thumbs_up" or "thumbs_down"
    comment = Column(Text, nullable=True)
    strategy = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)