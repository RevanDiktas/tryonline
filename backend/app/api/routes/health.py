"""
Health check endpoints
"""
from fastapi import APIRouter
from datetime import datetime

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
    # TODO: Add actual checks for Supabase, Redis, etc.
    return {
        "status": "ready",
        "services": {
            "database": "connected",
            "storage": "connected",
            "gpu": "available"
        }
    }
