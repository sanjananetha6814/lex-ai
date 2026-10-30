from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.chat import Conversation, Message
from app.models.user import User, UserRole
from app.auth import get_current_user, get_current_user_optional
from app.ai.service import default_ai_service
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    ChatQuestionRequest,
    ChatAnswerResponse,
)

router = APIRouter(prefix="", tags=["Chat & Conversations"])

def _get_or_create_demo_user(db: Session) -> User:
    demo = db.query(User).filter(User.email == "alex.morgan@workspace.lexai").first()
    if demo:
        return demo
    return db.query(User).first()

@router.post("/chat", response_model=ChatAnswerResponse)
def chat_direct(
    request: ChatQuestionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Direct legal question endpoint connecting RAG pipeline to LLM.
    Returns structured plain-language legal explanation with citations.
    """
    user = current_user or _get_or_create_demo_user(db)
    
    # 1. Run AI Service with RAG
    ai_result = default_ai_service.ask_question(
        question=request.message,
        language=request.language or "English"
    )

    conv_id = request.conversation_id
    msg_id = None

    # 2. If user or conversation context exists, record messages in DB
    if user:
        if not conv_id:
            conv = Conversation(
                user_id=user.id,
                title=request.message[:40] + ("..." if len(request.message) > 40 else ""),
                language=request.language or "English",
                is_saved=False
            )
            db.add(conv)
            db.flush()
            conv_id = conv.id

        # User message
        user_msg = Message(
            conversation_id=conv_id,
            role="user",
            content=request.message
        )
        db.add(user_msg)

        # Assistant message
        assistant_msg = Message(
            conversation_id=conv_id,
            role="assistant",
            content=ai_result.get("explanation", ""),
            sources=ai_result.get("sources", [])
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        msg_id = assistant_msg.id

    return ChatAnswerResponse(
        title=ai_result.get("title", "Simple Explanation"),
        explanation=ai_result.get("explanation", ""),
        implication=ai_result.get("implication", ""),
        checks=ai_result.get("checks", []),
        consult=ai_result.get("consult", ""),
        sources=ai_result.get("sources", []),
        caveat=ai_result.get("caveat", "General legal information, not legal advice."),
        is_grounded=ai_result.get("is_grounded", False),
        conversation_id=conv_id,
        message_id=msg_id
    )

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = Conversation(
        user_id=current_user.id,
        title=conv_in.title or "New Legal Query",
        language=conv_in.language or "English",
        is_saved=False
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv

@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Conversation).options(joinedload(Conversation.messages))
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Conversation.user_id == current_user.id)

    conversations = query.order_by(Conversation.id.desc()).offset(skip).limit(limit).all()
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} was not found."
        )

    # Ownership check
    if current_user.role != UserRole.ADMIN and conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this conversation."
        )

    return conv

@router.post("/conversations/{conversation_id}/messages", response_model=ChatAnswerResponse)
def send_message_to_conversation(
    conversation_id: int,
    msg_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} was not found."
        )

    if current_user.role != UserRole.ADMIN and conv.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to send messages to this conversation."
        )

    # 1. Record user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=msg_in.content
    )
    db.add(user_msg)

    # 2. Run AI RAG pipeline
    ai_result = default_ai_service.ask_question(
        question=msg_in.content,
        language=msg_in.language or conv.language or "English"
    )

    # 3. Record assistant response
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=ai_result.get("explanation", ""),
        sources=ai_result.get("sources", [])
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return ChatAnswerResponse(
        title=ai_result.get("title", "Simple Explanation"),
        explanation=ai_result.get("explanation", ""),
        implication=ai_result.get("implication", ""),
        checks=ai_result.get("checks", []),
        consult=ai_result.get("consult", ""),
        sources=ai_result.get("sources", []),
        caveat=ai_result.get("caveat", "General legal information, not legal advice."),
        is_grounded=ai_result.get("is_grounded", False),
        conversation_id=conversation_id,
        message_id=assistant_msg.id
    )
