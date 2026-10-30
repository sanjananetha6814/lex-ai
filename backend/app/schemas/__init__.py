from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    UserProfileResponse,
    TokenResponse,
)
from app.schemas.lawyer import LawyerResponse, LawyerProfileResponse
from app.schemas.consultation import ConsultationCreate, ConsultationResponse
from app.schemas.document import DocumentResponse, DocumentAnalysisResponse, ClauseFinding
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ChatQuestionRequest,
    ChatAnswerResponse,
)

__all__ = [
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "UserProfileResponse",
    "TokenResponse",
    "LawyerResponse",
    "LawyerProfileResponse",
    "ConsultationCreate",
    "ConsultationResponse",
    "DocumentResponse",
    "DocumentAnalysisResponse",
    "ClauseFinding",
    "ConversationCreate",
    "ConversationResponse",
    "MessageCreate",
    "MessageResponse",
    "ChatQuestionRequest",
    "ChatAnswerResponse",
]
