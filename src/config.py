"""Configuration management for Document Extractor."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # API Keys
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/document_extractor",
        description="PostgreSQL connection string"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery"
    )
    
    # Ollama
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API host")
    ollama_model: str = Field(default="llama3.2", description="Default Ollama model")
    
    # Storage
    upload_dir: Path = Field(default=Path("./uploads"), description="Directory for uploaded files")
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    
    # Processing
    ocr_languages: list[str] = Field(default=["en"], description="OCR language codes")
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence for auto-accept")
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", 
        description="Logging level"
    )
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
