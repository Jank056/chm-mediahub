"""Routers package."""

from .analytics import router as analytics_router
from .auth import router as auth_router
from .chat import router as chat_router
from .clients import router as clients_router
from .linkedin import router as linkedin_router
from .oauth import router as oauth_router
from .reports import router as reports_router
from .users import router as users_router
from .webhook import router as webhook_router
from .x import router as x_router
from .youtube import router as youtube_router

__all__ = [
    "analytics_router",
    "auth_router",
    "chat_router",
    "clients_router",
    "linkedin_router",
    "oauth_router",
    "reports_router",
    "users_router",
    "webhook_router",
    "x_router",
    "youtube_router",
]
