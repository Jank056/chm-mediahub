"""Routers package."""

from .analytics import router as analytics_router
from .auth import router as auth_router
from .chat import router as chat_router
from .clients import router as clients_router
from .reports import router as reports_router
from .users import router as users_router
from .webhook import router as webhook_router

__all__ = [
    "analytics_router",
    "auth_router",
    "chat_router",
    "clients_router",
    "reports_router",
    "users_router",
    "webhook_router",
]
