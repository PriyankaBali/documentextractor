"""Database models for PostgreSQL with SQLAlchemy."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, Integer, String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import get_settings

Base = declarative_base()


class Document(Base):
    """Document record in database."""
    
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    document_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    
    # JSONB columns for flexible data storage
    extracted_data = Column(JSONB, nullable=False, default={})
    confidences = Column(JSONB, nullable=False, default={})
    overall_confidence = Column(Float, default=0.0)
    
    # Raw data for debugging/reprocessing
    ocr_text = Column(Text, nullable=True)
    raw_llm_response = Column(Text, nullable=True)
    
    # Error tracking
    errors = Column(JSONB, nullable=False, default=[])
    requires_review = Column(Boolean, default=False)
    
    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExtractionJob(Base):
    """Batch extraction job tracking."""
    
    __tablename__ = "extraction_jobs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status = Column(String(50), nullable=False, default="pending")
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    
    callback_url = Column(String(500), nullable=True)
    
    # Store document IDs
    document_ids = Column(JSONB, nullable=False, default=[])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


# Database connection
def get_engine():
    """Get async database engine."""
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


def get_session_maker():
    """Get async session maker."""
    engine = get_engine()
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
