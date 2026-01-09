# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Chat service for managing conversations and messages.

Provides business logic for:
- Creating and managing conversations
- Sending and receiving messages
- Read receipts and delivery status
"""

import logging
from datetime import datetime, UTC
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chat_message import ChatMessage, MessageContentType, MessageStatus
from app.domain.entities.conversation import Conversation, ConversationParticipant, ConversationType
from app.domain.ports.websocket import MessageType, WebSocketMessage, WebSocketPort
from app.infrastructure.database.models.chat_message import ChatMessageModel
from app.infrastructure.database.models.conversation import (
    ConversationModel,
    ConversationParticipantModel,
)

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for managing chat functionality.
    
    Handles conversation creation, message sending, and real-time
    delivery through WebSockets.
    """
    
    def __init__(
        self,
        session: AsyncSession,
        ws_manager: WebSocketPort | None = None,
    ) -> None:
        """
        Initialize the chat service.
        
        Args:
            session: Database session
            ws_manager: WebSocket manager for real-time delivery
        """
        self._session = session
        self._ws_manager = ws_manager
    
    # =========================================
    # Conversations
    # =========================================
    
    async def get_or_create_direct_conversation(
        self,
        user_id: UUID,
        other_user_id: UUID,
        tenant_id: UUID,
    ) -> Conversation:
        """
        Get existing direct conversation or create new one.
        
        Args:
            user_id: First participant
            other_user_id: Second participant
            tenant_id: Tenant ID
            
        Returns:
            Conversation entity
        """
        # Look for existing direct conversation between these users
        stmt = (
            select(ConversationModel)
            .join(ConversationParticipantModel)
            .where(
                ConversationModel.type == ConversationType.DIRECT.value,
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.is_deleted == False,
            )
            .where(
                ConversationParticipantModel.user_id.in_([user_id, other_user_id])
            )
            .group_by(ConversationModel.id)
            .having(
                # Both users must be participants
                func.count(ConversationParticipantModel.user_id) == 2
            )
        )
        
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            return self._conversation_to_entity(existing)
        
        # Create new conversation
        conversation_id = uuid4()
        now = datetime.now(UTC)
        
        conversation_model = ConversationModel(
            id=conversation_id,
            tenant_id=tenant_id,
            type=ConversationType.DIRECT.value,
            created_at=now,
            updated_at=now,
        )
        
        self._session.add(conversation_model)
        
        # Add participants
        for uid in [user_id, other_user_id]:
            participant = ConversationParticipantModel(
                conversation_id=conversation_id,
                user_id=uid,
                joined_at=now,
                role="member",
            )
            self._session.add(participant)
        
        await self._session.flush()
        
        return Conversation(
            id=conversation_id,
            tenant_id=tenant_id,
            type=ConversationType.DIRECT,
            participants=[
                ConversationParticipant(user_id=user_id),
                ConversationParticipant(user_id=other_user_id),
            ],
            created_at=now,
            updated_at=now,
        )
    
    async def create_group_conversation(
        self,
        name: str,
        creator_id: UUID,
        participant_ids: list[UUID],
        tenant_id: UUID,
        description: str | None = None,
    ) -> Conversation:
        """
        Create a new group conversation.
        
        Args:
            name: Group name
            creator_id: User creating the group
            participant_ids: Initial participants
            tenant_id: Tenant ID
            description: Optional description
            
        Returns:
            Created conversation entity
        """
        conversation_id = uuid4()
        now = datetime.now(UTC)
        
        conversation_model = ConversationModel(
            id=conversation_id,
            tenant_id=tenant_id,
            type=ConversationType.GROUP.value,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )
        
        self._session.add(conversation_model)
        
        # Add creator as owner
        creator_participant = ConversationParticipantModel(
            conversation_id=conversation_id,
            user_id=creator_id,
            joined_at=now,
            role="owner",
        )
        self._session.add(creator_participant)
        
        participants = [ConversationParticipant(user_id=creator_id, role="owner")]
        
        # Add other participants
        for uid in participant_ids:
            if uid != creator_id:
                participant = ConversationParticipantModel(
                    conversation_id=conversation_id,
                    user_id=uid,
                    joined_at=now,
                    role="member",
                )
                self._session.add(participant)
                participants.append(ConversationParticipant(user_id=uid))
        
        await self._session.flush()
        
        return Conversation(
            id=conversation_id,
            tenant_id=tenant_id,
            type=ConversationType.GROUP,
            name=name,
            description=description,
            participants=participants,
            created_at=now,
            updated_at=now,
        )
    
    async def get_conversation(
        self,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation | None:
        """
        Get a conversation by ID if user is a participant.
        
        Args:
            conversation_id: Conversation ID
            user_id: Requesting user (must be participant)
            
        Returns:
            Conversation entity or None
        """
        stmt = (
            select(ConversationModel)
            .join(ConversationParticipantModel)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.is_deleted == False,
                ConversationParticipantModel.user_id == user_id,
            )
        )
        
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._conversation_to_entity(model) if model else None
    
    async def get_user_conversations(
        self,
        user_id: UUID,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            limit: Max results
            offset: Pagination offset
            
        Returns:
            List of conversations
        """
        stmt = (
            select(ConversationModel)
            .join(ConversationParticipantModel)
            .where(
                ConversationModel.tenant_id == tenant_id,
                ConversationModel.is_deleted == False,
                ConversationParticipantModel.user_id == user_id,
            )
            .order_by(ConversationModel.last_message_at.desc().nullsfirst())
            .limit(limit)
            .offset(offset)
        )
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._conversation_to_entity(m) for m in models]
    
    # =========================================
    # Messages
    # =========================================
    
    async def send_message(
        self,
        conversation_id: UUID,
        sender_id: UUID,
        content: str,
        content_type: MessageContentType = MessageContentType.TEXT,
        metadata: dict | None = None,
        reply_to_id: UUID | None = None,
    ) -> ChatMessage:
        """
        Send a message in a conversation.
        
        Args:
            conversation_id: Target conversation
            sender_id: Sender user ID
            content: Message content
            content_type: Type of content
            metadata: Optional metadata
            reply_to_id: Optional reply reference
            
        Returns:
            Created message entity
        """
        # Get conversation to verify access and get tenant_id
        stmt = (
            select(ConversationModel)
            .join(ConversationParticipantModel)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.is_deleted == False,
                ConversationParticipantModel.user_id == sender_id,
            )
        )
        
        result = await self._session.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        # Create message
        message_id = uuid4()
        now = datetime.now(UTC)
        
        message_model = ChatMessageModel(
            id=message_id,
            tenant_id=conversation.tenant_id,
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            content_type=content_type.value,
            metadata=metadata or {},
            status=MessageStatus.SENT.value,
            reply_to_id=reply_to_id,
            created_at=now,
            updated_at=now,
        )
        
        self._session.add(message_model)
        
        # Update conversation
        conversation.last_message_id = message_id  # type: ignore[assignment]
        conversation.last_message_at = now
        conversation.last_message_preview = content[:100] if content else None
        conversation.message_count += 1
        conversation.updated_at = now
        
        await self._session.flush()
        
        message = ChatMessage(
            id=message_id,
            tenant_id=UUID(str(conversation.tenant_id)),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            content_type=content_type,
            metadata=metadata or {},
            status=MessageStatus.SENT,
            reply_to_id=reply_to_id,
            created_at=now,
            updated_at=now,
        )
        
        # Send via WebSocket if available
        if self._ws_manager:
            await self._deliver_message(message, conversation)
        
        return message
    
    async def _deliver_message(
        self,
        message: ChatMessage,
        conversation: ConversationModel,
    ) -> None:
        """Deliver message via WebSocket to all participants."""
        if not self._ws_manager:
            return
        
        ws_message = WebSocketMessage(
            type=MessageType.CHAT_MESSAGE,
            payload={
                "id": str(message.id),
                "conversation_id": str(message.conversation_id),
                "sender_id": str(message.sender_id),
                "content": message.content,
                "content_type": message.content_type.value,
                "metadata": message.metadata,
                "reply_to_id": str(message.reply_to_id) if message.reply_to_id else None,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            },
            sender_id=message.sender_id,
            room_id=str(message.conversation_id),
            message_id=message.id,
        )
        
        # Send to room (all participants)
        await self._ws_manager.send_to_room(
            str(message.conversation_id),
            ws_message,
        )
    
    async def get_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 50,
        before: datetime | None = None,
        after: datetime | None = None,
    ) -> list[ChatMessage]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: Requesting user (must be participant)
            limit: Max messages
            before: Get messages before this timestamp
            after: Get messages after this timestamp
            
        Returns:
            List of messages
        """
        # Verify user is participant
        participant_check = (
            select(ConversationParticipantModel)
            .where(
                ConversationParticipantModel.conversation_id == conversation_id,
                ConversationParticipantModel.user_id == user_id,
            )
        )
        
        result = await self._session.execute(participant_check)
        if not result.scalar_one_or_none():
            raise ValueError("Access denied")
        
        # Build query
        stmt = (
            select(ChatMessageModel)
            .where(
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.is_deleted == False,
            )
        )
        
        if before:
            stmt = stmt.where(ChatMessageModel.created_at < before)
        
        if after:
            stmt = stmt.where(ChatMessageModel.created_at > after)
        
        stmt = stmt.order_by(ChatMessageModel.created_at.desc()).limit(limit)
        
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        
        return [self._message_to_entity(m) for m in reversed(models)]
    
    async def mark_messages_read(
        self,
        conversation_id: UUID,
        user_id: UUID,
        message_ids: list[UUID] | None = None,
    ) -> int:
        """
        Mark messages as read by user.
        
        Args:
            conversation_id: Conversation ID
            user_id: Reader's user ID
            message_ids: Specific messages (or all if None)
            
        Returns:
            Number of messages marked
        """
        now = datetime.now(UTC)
        
        # Update participant's last_read
        await self._session.execute(
            update(ConversationParticipantModel)
            .where(
                ConversationParticipantModel.conversation_id == conversation_id,
                ConversationParticipantModel.user_id == user_id,
            )
            .values(last_read_at=now)
        )
        
        # If specific messages, mark them as read
        if message_ids:
            result = await self._session.execute(
                update(ChatMessageModel)
                .where(
                    ChatMessageModel.id.in_(message_ids),
                    ChatMessageModel.conversation_id == conversation_id,
                    ChatMessageModel.sender_id != user_id,  # Don't mark own messages
                    ChatMessageModel.status != MessageStatus.READ.value,
                )
                .values(
                    status=MessageStatus.READ.value,
                    read_at=now,
                )
            )
            return result.rowcount  # type: ignore
        
        return 0
    
    # =========================================
    # Entity conversion
    # =========================================
    
    def _conversation_to_entity(self, model: ConversationModel) -> Conversation:
        """Convert ConversationModel to Conversation entity."""
        participants = []
        for p in model.participants:
            participants.append(
                ConversationParticipant(
                    user_id=p.user_id,
                    joined_at=p.joined_at,
                    is_muted=p.is_muted,
                    muted_until=p.muted_until,
                    last_read_message_id=p.last_read_message_id,
                    last_read_at=p.last_read_at,
                    role=p.role,
                    nickname=p.nickname,
                )
            )
        
        return Conversation(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            type=ConversationType(model.type),
            participants=participants,
            name=model.name,
            description=model.description,
            avatar_url=model.avatar_url,
            last_message_id=UUID(str(model.last_message_id)) if model.last_message_id else None,
            last_message_at=model.last_message_at,
            last_message_preview=model.last_message_preview,
            message_count=model.message_count,
            is_archived=model.is_archived,
            send_permission=model.send_permission,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _message_to_entity(self, model: ChatMessageModel) -> ChatMessage:
        """Convert ChatMessageModel to ChatMessage entity."""
        return ChatMessage(
            id=UUID(str(model.id)),
            tenant_id=UUID(str(model.tenant_id)),
            conversation_id=UUID(str(model.conversation_id)),
            sender_id=UUID(str(model.sender_id)),
            content=model.content,
            content_type=MessageContentType(model.content_type),
            metadata=model.metadata,
            status=MessageStatus(model.status),
            delivered_at=model.delivered_at,
            read_at=model.read_at,
            reply_to_id=UUID(str(model.reply_to_id)) if model.reply_to_id else None,
            reactions=model.reactions,
            is_edited=model.is_edited,
            edited_at=model.edited_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
