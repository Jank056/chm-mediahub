"""CHM MediaHub - FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
from database import engine
from models import Base
from routers import (
    analytics_router,
    auth_router,
    chat_router,
    clients_router,
    linkedin_router,
    oauth_router,
    reports_router,
    users_router,
    webhook_router,
    x_router,
    youtube_router,
)
from services.redis_store import RedisStore
from services.scheduler import start_scheduler, stop_scheduler
from middleware.rate_limit import limiter

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - create tables on startup, cleanup on shutdown."""
    # Startup: create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check Redis connectivity
    redis_ok = await RedisStore.health_check()
    if redis_ok:
        print("✓ Redis connection established")
    else:
        print("⚠ Redis not available - job storage will not persist")

    # Security check: Warn if using default JWT secret in production
    if not settings.debug and settings.jwt_secret == "dev-secret-change-in-production":
        print("⚠ SECURITY WARNING: Using default JWT secret in production!")
        print("  Set JWT_SECRET environment variable to a secure random value.")
        # Don't exit - just warn loudly

    # Start background scheduler for periodic tasks
    start_scheduler()

    yield

    # Shutdown: stop scheduler and close Redis connection pool
    stop_scheduler()
    await RedisStore.close()


app = FastAPI(
    title="CHM MediaHub API",
    description="Unified client portal for Community Health Media",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(clients_router)
app.include_router(linkedin_router)
app.include_router(oauth_router)
app.include_router(reports_router)
app.include_router(users_router)
app.include_router(webhook_router)
app.include_router(x_router)
app.include_router(youtube_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "chm-mediahub"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CHM MediaHub API",
        "version": "0.1.0",
        "docs": "/docs",
    }
