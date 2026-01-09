# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""Chat REST API endpoints.

Provides endpoints for:
- Conversation management (list, create, get)
- Message management (list, send, mark as read)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_current_user
from app.infrastructure.database.connection import get_db_session
from app.infrastructure.database.models.conversation import (
    ConversationModel,
    ConversationParticipantModel,
)
from app.infrastructure.database.models.chat_message import ChatMessageModel


router = APIRouter(prefix="/chat")


# ===========================================
# Schemas
# ===========================================

class ParticipantResponse(BaseModel):
    """Participant in a conversation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    role: str
    nickname: Optional[str] = None
    joined_at: str


class ConversationResponse(BaseModel):
    """Conversation response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    type: str
    name: Optional[str] = None
    participants: list[ParticipantResponse] = []
    last_message_preview: Optional[str] = None
    last_message_at: Optional[str] = None
    unread_count: int = 0
    created_at: str


class MessageResponse(BaseModel):
    """Chat message response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    conversation_id: str
    sender_id: str
    content: str
    content_type: str
    metadata: Optional[dict] = None
    status: str
    reply_to_id: Optional[str] = None
    reactions: Optional[dict] = None
    is_edited: bool = False
    created_at: str


class CreateDirectConversationRequest(BaseModel):
    """Request to create a direct conversation."""
    
    user_id: str = Field(..., description="ID of user to chat with")


class CreateGroupConversationRequest(BaseModel):
    """Request to create a group conversation."""
    
    name: str = Field(..., min_length=1, max_length=100)
    participant_ids: list[str] = Field(..., min_length=1)


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: str = Field(default="text")
    reply_to_id: Optional[str] = None
    metadata: Optional[dict] = None


class MarkReadRequest(BaseModel):
    """Request to mark messages as read."""
    
    message_ids: list[str] = Field(..., min_length=1)


class ConversationListResponse(BaseModel):
    """List of conversations."""
    
    items: list[ConversationResponse]
    total: int


class MessageListResponse(BaseModel):
    """List of messages."""
    
    items: list[MessageResponse]
    has_more: bool


# ===========================================
# Endpoints
# ===========================================

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List user's conversations."""
    # Get conversations where user is a participant
    query = (
        select(ConversationModel)
        .join(ConversationParticipantModel)
        .where(
            ConversationParticipantModel.user_id == current_user.id,
        )
        .options(selectinload(ConversationModel.participants))
        .order_by(ConversationModel.last_message_at.desc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    
    result = await session.execute(query)
    conversations = result.scalars().unique().all()
    
    # Count total
    count_query = (
        select(ConversationModel.id)
        .join(ConversationParticipantModel)
        .where(
            ConversationParticipantModel.user_id == current_user.id,
        )
    )
    count_result = await session.execute(count_query)
    total = len(count_result.all())
    
    def get_unread_count_for_user(conv, user_id: UUID) -> int:
        """Calculate unread count for a user in a conversation."""
        for p in conv.participants:
            if p.user_id == user_id:
                if not p.last_read_at:
                    # Never read - all messages are unread
                    return conv.message_count if hasattr(conv, 'message_count') else 0
                if conv.last_message_at and p.last_read_at < conv.last_message_at:
                    # Has unread messages (simplified - returns 1 if any unread)
                    return 1
                return 0
        return 0
    
    return ConversationListResponse(
        items=[
            ConversationResponse(
                id=str(conv.id),
                type=conv.type,
                name=conv.name,
                participants=[
                    ParticipantResponse(
                        user_id=str(p.user_id),
                        role=p.role,
                        nickname=p.nickname,
                        joined_at=p.joined_at.isoformat(),
                    )
                    for p in conv.participants
                ],
                last_message_preview=conv.last_message_preview,
                last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None,
                unread_count=get_unread_count_for_user(conv, current_user.id),
                created_at=conv.created_at.isoformat(),
            )
            for conv in conversations
        ],
        total=total,
    )


@router.post("/conversations/direct", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_direct_conversation(
    request: CreateDirectConversationRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Create or get a direct conversation with another user."""
    from app.application.services.chat_service import ChatService
    
    chat_service = ChatService(session)
    conversation = await chat_service.get_or_create_direct_conversation(
        user_id=current_user.id,
        other_user_id=UUID(request.user_id),
        tenant_id=current_user.tenant_id,
    )
    
    return ConversationResponse(
        id=str(conversation.id),
        type=conversation.type.value,
        name=conversation.name,
        participants=[
            ParticipantResponse(
                user_id=str(p.user_id),
                role=getattr(p.role, 'value', p.role),  # type: ignore[arg-type]
                nickname=p.nickname,
                joined_at=p.joined_at.isoformat() if p.joined_at else "",
            )
            for p in conversation.participants
        ],
        last_message_preview=None,
        last_message_at=None,
        unread_count=0,
        created_at=conversation.created_at.isoformat() if conversation.created_at else "",
    )


@router.post("/conversations/group", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group_conversation(
    request: CreateGroupConversationRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a group conversation."""
    from app.application.services.chat_service import ChatService
    
    chat_service = ChatService(session)
    conversation = await chat_service.create_group_conversation(
        name=request.name,
        creator_id=current_user.id,
        participant_ids=[UUID(pid) for pid in request.participant_ids],
        tenant_id=current_user.tenant_id,
    )
    
    return ConversationResponse(
        id=str(conversation.id),
        type=conversation.type.value,
        name=conversation.name,
        participants=[
            ParticipantResponse(
                user_id=str(p.user_id),
                role=getattr(p.role, 'value', p.role),  # type: ignore[arg-type]
                nickname=p.nickname,
                joined_at=p.joined_at.isoformat() if p.joined_at else "",
            )
            for p in conversation.participants
        ],
        last_message_preview=None,
        last_message_at=None,
        unread_count=0,
        created_at=conversation.created_at.isoformat() if conversation.created_at else "",
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a specific conversation."""
    # Verify user is a participant
    query = (
        select(ConversationModel)
        .join(ConversationParticipantModel)
        .where(
            ConversationModel.id == conversation_id,
            ConversationParticipantModel.user_id == current_user.id,
        )
        .options(selectinload(ConversationModel.participants))
    )
    
    result = await session.execute(query)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )
    
    return ConversationResponse(
        id=str(conversation.id),
        type=conversation.type,
        name=conversation.name,
        participants=[
            ParticipantResponse(
                user_id=str(p.user_id),
                role=p.role,
                nickname=p.nickname,
                joined_at=p.joined_at.isoformat(),
            )
            for p in conversation.participants
        ],
        last_message_preview=conversation.last_message_preview,
        last_message_at=conversation.last_message_at.isoformat() if conversation.last_message_at else None,
        unread_count=0,
        created_at=conversation.created_at.isoformat(),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conversation_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[str] = Query(default=None, description="ISO datetime to fetch messages before"),
):
    """List messages in a conversation."""
    from datetime import datetime
    
    # Verify user is a participant
    participant_query = select(ConversationParticipantModel).where(
        ConversationParticipantModel.conversation_id == conversation_id,
        ConversationParticipantModel.user_id == current_user.id,
    )
    result = await session.execute(participant_query)
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied",
        )
    
    # Build messages query
    query = (
        select(ChatMessageModel)
        .where(
            ChatMessageModel.conversation_id == conversation_id,
            ChatMessageModel.deleted_at.is_(None),
        )
    )
    
    if before:
        before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
        query = query.where(ChatMessageModel.created_at < before_dt)
    
    query = query.order_by(ChatMessageModel.created_at.desc()).limit(limit + 1)
    
    result = await session.execute(query)
    messages = result.scalars().all()
    
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:-1]
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    return MessageListResponse(
        items=[
            MessageResponse(
                id=str(msg.id),
                conversation_id=str(msg.conversation_id),
                sender_id=str(msg.sender_id),
                content=msg.content,
                content_type=msg.content_type,
                metadata=msg.metadata,
                status=msg.status,
                reply_to_id=str(msg.reply_to_id) if msg.reply_to_id else None,
                reactions=msg.reactions,
                is_edited=msg.is_edited,
                created_at=msg.created_at.isoformat(),
            )
            for msg in messages
        ],
        has_more=has_more,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Send a message to a conversation."""
    from app.application.services.chat_service import ChatService
    from app.domain.entities.chat_message import MessageContentType
    
    chat_service = ChatService(session)
    
    try:
        content_type = MessageContentType(request.content_type)
    except ValueError:
        content_type = MessageContentType.TEXT
    
    message = await chat_service.send_message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=request.content,
        content_type=content_type,
        reply_to_id=UUID(request.reply_to_id) if request.reply_to_id else None,
        metadata=request.metadata,
    )
    
    return MessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        sender_id=str(message.sender_id),
        content=message.content,
        content_type=message.content_type.value,
        metadata=message.metadata,
        status=message.status.value,
        reply_to_id=str(message.reply_to_id) if message.reply_to_id else None,
        reactions=message.reactions,
        is_edited=message.is_edited,
        created_at=message.created_at.isoformat() if message.created_at else "",
    )


@router.post("/conversations/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_messages_read(
    conversation_id: UUID,
    request: MarkReadRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
):
    """Mark messages as read."""
    from app.application.services.chat_service import ChatService
    
    chat_service = ChatService(session)
    await chat_service.mark_messages_read(
        conversation_id=conversation_id,
        user_id=current_user.id,
        message_ids=[UUID(mid) for mid in request.message_ids],
    )
