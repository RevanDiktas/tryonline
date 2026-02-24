"""
Configuration settings for TryOn Backend API
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
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
    supabase_jwt_secret: str = ""  # JWT secret (Project Settings → API → JWT Secret) for verifying access tokens
    
    # Redis (for Celery)
    redis_url: str = "redis://localhost:6379/0"
    
    # RunPod
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""
    
    # Storage Buckets
    photos_bucket: str = "photos"
    avatars_bucket: str = "avatars"
    garments_bucket: str = "garments"

    @field_validator("photos_bucket", "avatars_bucket", "garments_bucket", mode="after")
    @classmethod
    def strip_bucket_names(cls, v: str) -> str:
        return v.strip()
    
    # Processing
    avatar_processing_timeout: int = 300  # 5 minutes

    # Shopify (optional)
    shopify_webhook_secret: str = ""  # For HMAC verification of orders/paid
    shopify_client_id: str = ""  # From Partners app (API key)
    shopify_client_secret: str = ""  # From Partners app (Client secret)
    frontend_app_url: str = "https://tryonline.vercel.app"  # Base URL of Next.js app for OAuth redirect
    backend_public_url: str = ""  # Public URL of this API (e.g. https://api.railway.app) for OAuth callback

    # Server (Railway/Render set PORT at runtime)
    port: int = 8000

    # CORS: comma-separated origins, e.g. https://app.yourdomain.com,https://yourapp.vercel.app
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
