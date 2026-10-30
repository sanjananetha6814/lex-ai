from app.routers.auth import router as auth_router
from app.routers.lawyers import router as lawyers_router
from app.routers.consultations import router as consultations_router
from app.routers.documents import router as documents_router
from app.routers.chat import router as chat_router
from app.routers.notifications import router as notifications_router

__all__ = [
    "auth_router",
    "lawyers_router",
    "consultations_router",
    "documents_router",
    "chat_router",
    "notifications_router",
]

