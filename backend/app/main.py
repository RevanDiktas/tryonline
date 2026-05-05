"""
TryOn Backend API - Main Application Entry Point
"""
import asyncio
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.api.routes import auth, avatar, measurements, events, health, webhooks, analytics, products, addresses, checkout_profile, shopify, brand, garments, wishlist, draping


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    print(f"Starting {settings.app_name}...")

    # Drape dispatcher: opt-in via env (default on if RunPod is configured).
    dispatcher_task = None
    stop_event: asyncio.Event | None = None
    enabled = os.getenv("DRAPE_DISPATCHER_ENABLED", "1") == "1"
    if enabled and settings.runpod_api_key and settings.runpod_draping_endpoint_id:
        from app.services.drape_dispatcher import dispatcher_loop
        stop_event = asyncio.Event()
        dispatcher_task = asyncio.create_task(dispatcher_loop(stop_event))
    else:
        print("[main] Drape dispatcher not started (disabled or RunPod not configured)")

    try:
        yield
    finally:
        print(f"Shutting down {settings.app_name}...")
        if stop_event is not None:
            stop_event.set()
        if dispatcher_task is not None:
            try:
                await asyncio.wait_for(dispatcher_task, timeout=5.0)
            except asyncio.TimeoutError:
                dispatcher_task.cancel()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API for TryOn virtual fitting room platform",
    version=settings.api_version,
    lifespan=lifespan,
)

# Configure CORS from environment (comma-separated); production sets CORS_ORIGINS
def _cors_origins() -> list[str]:
    raw = (settings.cors_origins or "").strip()
    if not raw:
        return ["http://localhost:3000", "http://localhost:3001"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter (in-memory; suitable for single-instance Railway deploy)
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
    )

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(avatar.router, prefix="/api/avatar", tags=["Avatar"])
app.include_router(measurements.router, prefix="/api/measurements", tags=["Measurements"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(addresses.router, prefix="/api/addresses", tags=["Addresses"])
app.include_router(checkout_profile.router, prefix="/api/checkout-profile", tags=["Checkout Profile"])
app.include_router(shopify.router, prefix="/api/shopify", tags=["Shopify"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(brand.router, prefix="/api/brand", tags=["Brand"])
app.include_router(garments.router, prefix="/api/garments", tags=["Garments"])
app.include_router(wishlist.router, prefix="/api/wishlist", tags=["Wishlist"])
app.include_router(draping.router, prefix="/api/draping", tags=["Draping"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.api_version,
        "status": "running"
    }


@app.get("/routes")
async def list_routes():
    """Debug: list all registered routes. Only available when DEBUG=true."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    routes = []
    for r in app.routes:
        path = getattr(r, "path", None)
        if path is None:
            continue
        methods = list(r.methods) if getattr(r, "methods", None) else []
        routes.append({"path": path, "methods": methods or ["GET"]})
    return {"routes": routes, "shopify_ok": any("/api/shopify" in (r.get("path") or "") for r in routes)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
