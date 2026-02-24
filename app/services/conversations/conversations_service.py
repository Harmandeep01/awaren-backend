# app/services/history_crud.py (UPDATED with Conversation logic)

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from app.models.chat import ChatHistory, Conversation  # <-- Import Conversation
from uuid import UUID

# --- CONVERSATION CRUD ---


async def create_new_conversation(
    session: AsyncSession, user_id: UUID, initial_title: str = "New Conversation"
) -> Conversation:
    """Creates a new conversation session for the user."""
    new_conversation = Conversation(user_id=user_id, title=initial_title)
    session.add(new_conversation)
    await session.commit()
    await session.refresh(new_conversation)
    return new_conversation


async def get_conversations_by_user(
    session: AsyncSession, user_id: UUID
) -> List[Conversation]:
    """Retrieves all conversations for a user, ordered by creation date."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.created_at))
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_conversation_by_id(
    session: AsyncSession, conversation_id: UUID, user_id: UUID
) -> Optional[Conversation]:
    """Retrieves a specific conversation, ensuring it belongs to the user."""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# --- CHAT HISTORY CRUD (MODIFIED) ---


async def add_message_to_history(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,  # <-- NEW PARAMETER
    role: str,
    content: str,
):
    """Stores a single message tied to a specific conversation."""
    new_message = ChatHistory(
        user_id=user_id,
        conversation_id=conversation_id,  # <-- USE NEW PARAMETER
        role=role,
        content=content,
    )
    session.add(new_message)
    # NOTE: We COMMIT in the background task now, so we remove the commit here.
    # We will let the calling function (the background task) handle the commit.
    return new_message


# --- GET HISTORY (MODIFIED) ---


async def get_last_n_messages(
    session: AsyncSession,
    conversation_id: UUID,  # <-- CHANGED PARAMETER to focus on Conversation ID
    n: int = 10,
) -> List[Dict]:
    """
    Retrieves the last N messages for a CONVERSATION.
    """
    stmt = (
        select(ChatHistory)
        .where(
            ChatHistory.conversation_id == conversation_id
        )  # <-- FILTER BY CONVERSATION
        .order_by(desc(ChatHistory.timestamp))
        .limit(n)
    )

    result = await session.execute(stmt)
    messages = result.scalars().all()

    formatted_history = []
    for msg in reversed(messages):
        formatted_history.append({"role": msg.role, "content": msg.content})

    return formatted_history


async def delete_conversation_by_id(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
):
    stmt = (
        delete(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .returning(Conversation.id)
    )

    result = await session.execute(stmt)
    await session.commit()

    return result.scalar_one_or_none()


async def update_conversation_title(session: AsyncSession, conversation_id: UUID, user_id: UUID, new_title: str):
    """
    Updates the title of a specific conversation in the database.
    """
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if conversation:
        conversation.title = new_title
        await session.commit()
        await session.refresh(conversation)
        return conversation
    return None

async def get_full_conversation_messages(
    session: AsyncSession, 
    conversation_id: UUID, 
) -> List[Dict]:
    """Retrieves ALL messages for a conversation."""
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.conversation_id == conversation_id)
        .order_by(ChatHistory.timestamp) # Order by ascending time
    )
    
    result = await session.execute(stmt)
    messages = result.scalars().all()
    
    # Format the messages (we don't need to reverse since we ordered by timestamp ascending)
    formatted_history = []
    for msg in messages:
        formatted_history.append({
            "role": msg.role,
            "content": msg.content
        })
        
    return formatted_history