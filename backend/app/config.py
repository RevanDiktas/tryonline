"""
Configuration settings for TryOn Backend API
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Settings
    app_name: str = "TryOn API"
    debug: bool = False
    api_version: str = "v1"
    
    # Supabase
    supabase_url: str
    supabase_service_key: str  # Service role key for backend operations
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"
    
    # RunPod
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""
    
    # Storage Buckets
    photos_bucket: str = "photos"
    avatars_bucket: str = "avatars"
    
    # Processing
    avatar_processing_timeout: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
