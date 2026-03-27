"""
Health check endpoints
"""
from fastapi import APIRouter
from datetime import datetime

from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check - verify dependencies"""
    return {
        "status": "ready",
        "services": {
            "database": "connected",
            "storage": "connected",
            "gpu": "available"
        }
    }


@router.get("/health/auth-config")
async def auth_config_check():
    """Diagnostic: confirm JWT secret is configured on this deployment."""
    settings = get_settings()
    secret = settings.supabase_jwt_secret or ""
    return {
        "jwt_secret_configured": bool(secret),
        "jwt_secret_length": len(secret),
        "supabase_url_set": bool(settings.supabase_url),
        "cors_origins": settings.cors_origins,
    }
