"""
Application configuration using pydantic-settings
Centralized, type-safe, environment-based config
"""
from functools import lru_cache
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Application settings with validation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = Field(..., description="PostgreSQL connection string")
    
    # Neo4j
    neo4j_uri: str = Field(..., description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(..., description="Neo4j password")
    
    # Redis
    redis_url: str = Field(..., description="Redis connection string")
    
    # Celery
    celery_broker_url: str = Field(..., description="Celery broker URL")
    celery_result_backend: str = Field(..., description="Celery result backend")
    
    # LLM Provider
    llm_provider: Literal["openai", "azure", "anthropic", "deepseek"] = Field(default="openai")
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    openai_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    
    # DeepSeek
    deepseek_api_key: str = Field(default="")
    deepseek_model: str = Field(default="deepseek-chat")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    
    # Azure OpenAI
    azure_openai_endpoint: str = Field(default="")
    azure_openai_api_key: str = Field(default="")
    azure_openai_deployment: str = Field(default="")
    azure_openai_api_version: str = Field(default="2024-02-01")
    
    # Embeddings
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_device: str = Field(default="cpu")
    
    # REBEL
    rebel_model: str = Field(default="Babelscape/rebel-large")
    rebel_device: str = Field(default="cpu")
    
    # Application
    app_name: str = Field(default="RAG-KG-System")
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
    cors_origins: List[str] = Field(default='["http://localhost:3000"]')
    
    # Security
    secret_key: str = Field(..., description="Secret key for JWT")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60, gt=0)
    
    # File Upload
    max_upload_size: int = Field(default=52428800, description="Max file size in bytes")
    allowed_extensions: List[str] = Field(default='[".pdf"]')
    upload_dir: str = Field(default="./data/uploads")
    
    # Processing
    chunk_size: int = Field(default=512, gt=0)
    chunk_overlap: int = Field(default=50, ge=0)
    max_concurrent_jobs: int = Field(default=2, gt=0)
    
    # Canonicalization
    entity_similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_cluster_size: int = Field(default=50, gt=0)
    
    # Retrieval
    bm25_k1: float = Field(default=1.5, ge=0.0)
    bm25_b: float = Field(default=0.75, ge=0.0, le=1.0)
    top_k_retrieval: int = Field(default=10, gt=0)
    graph_hop_limit: int = Field(default=3, gt=0, le=5)
    graph_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Generation
    max_evidence_length: int = Field(default=4000, gt=0)
    answer_max_tokens: int = Field(default=500, gt=0)
    
    # Observability
    enable_tracing: bool = Field(default=False)
    otel_exporter_otlp_endpoint: str = Field(default="")
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v
    
    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_allowed_extensions(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [v]
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
