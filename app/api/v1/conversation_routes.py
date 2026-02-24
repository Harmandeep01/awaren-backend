# app/api/v1/conversation_routes.py (UPDATED with new history endpoint)
import logger
from app.db.db import AsyncSessionLocal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import auth 
from app.db.db import get_session
from app.services.conversations.conversations_service import get_conversations_by_user, get_last_n_messages, get_conversation_by_id, delete_conversation_by_id
from typing import List, Dict
from uuid import UUID
from app.models.chat import ChatHistory
from app.services.cache.redis_manager import CacheManager

router = APIRouter(prefix="/conversations")

# -----------------------------
# CONVERSATION LIST (SIDEBAR)
# -----------------------------
@router.get("", response_model=list[dict])
async def list_conversations(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(auth.get_current_user),
):
    """
    Returns a list of all conversations for the authenticated user (sidebar).
    Cached with a short TTL for fast UX.
    """
    user_id: UUID = current_user.user_id
    user_id_str = str(user_id)

    # 2. DB = source of truth
    conversations = await get_conversations_by_user(session, user_id)

    formatted = [
        {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
        }
        for c in conversations
    ]

    return formatted

# --- 2. Message History Retrieval Endpoint (GET /api/v1/conversations/{id}/messages) ---
@router.get("/{conversation_id}/messages", response_model=List[Dict])
async def get_conversation_messages(
    conversation_id: UUID, 
    session: AsyncSession = Depends(get_session), 
    current_user = Depends(auth.get_current_user)
):
    """
    Retrieves the full chronological message history for a specific conversation.
    """
    user_id_uuid: UUID = current_user.user_id

    # 1. Validation: Ensure the conversation exists and belongs to the user
    conversation = await get_conversation_by_id(session, conversation_id, user_id_uuid)
    
    if not conversation:
        # 404 Not Found is appropriate if the conversation doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    # 2. Retrieval: Fetch all messages for this conversation.
    # We call get_last_n_messages but set n=None or a very large number to get everything.
    # NOTE: We need to modify get_last_n_messages in history_crud.py to handle retrieving ALL messages.
    
    # Assuming get_last_n_messages is updated to return all if n is large (e.g., 99999)
    # OR, better yet, we create a new function for ALL history.
    
    # For now, we reuse the existing function with a large limit:
    all_messages = await get_last_n_messages(session, conversation_id, n=99999)
    
    # The get_last_n_messages function already returns data in the desired format:
    # [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}, ...]
    
    return all_messages

# app/services/history_crud.py (NEW FUNCTION FOR FULL HISTORY)


@router.delete("/{conversation_id}")
async def delete_conversation_messages(
    conversation_id: UUID, 
    session: AsyncSession = Depends(get_session), 
    current_user = Depends(auth.get_current_user)
):
    """
    Retrieves the full chronological message history for a specific conversation.
    """
    user_id_uuid: UUID = current_user.user_id

    # 1. Validation: Ensure the conversation exists and belongs to the user
    res = await delete_conversation_by_id(session, conversation_id, user_id_uuid)
   
    if not res:
        # 404 Not Found is appropriate if the conversation doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

# @router.post("/{conversation_id}/generate-title")
