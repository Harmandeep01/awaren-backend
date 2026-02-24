from fastapi import APIRouter, HTTPException
import json
from fastapi import Depends, HTTPException, Request, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import auth 
from app.db.db import get_session, AsyncSessionLocal
from app.services.memory.mem0_service import mem0
from app.services.chat import chat_service
from app.repo.prompt_repo import PromptRepo
from app.services.conversations.conversations_service import add_message_to_history, get_last_n_messages, create_new_conversation, get_conversation_by_id
from app.services.titles.generate_title import generate_and_store_title

from uuid import UUID

router = APIRouter(prefix="/chat")

# --- CHAT STREAM ENDPOINT ---
@router.post("/stream")
async def chat_stream(
    request: Request, 
    background_tasks: BackgroundTasks, 
    session: AsyncSession = Depends(get_session), 
    current_user = Depends(auth.get_current_user)
):
    payload = await request.json()
    user_input = payload.get("text", "")
    
    # NEW: Get optional conversation_id from payload
    conversation_id_str = payload.get("conversation_id")
    print(f"Convo id: {conversation_id_str}")
    if not user_input:
        raise HTTPException(status_code=400, detail="No text provided")

    user_id_uuid: UUID = current_user.user_id
    user_id_str = str(user_id_uuid)
    
    # =========================================================
    # 1. SESSION MANAGEMENT (Create or Retrieve Conversation)
    # =========================================================
    conversation = None
    if conversation_id_str:
        try:
            conversation_id_uuid = UUID(conversation_id_str)
            # Retrieve and validate the conversation belongs to the user
            conversation = await get_conversation_by_id(session, conversation_id_uuid, user_id_uuid)
            if not conversation:
                 raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid conversation_id format.")
    
    is_new_conversation = False

    if not conversation:
        conversation = await create_new_conversation(session, user_id_uuid)
        await session.commit()
        is_new_conversation = True

    
    # Get the final ID for use in history/persistence
    conversation_id_uuid = conversation.id


    # =========================================================
    # 2. SHORT-TERM CONTEXT: Retrieve History 
    # =========================================================
    # Now retrieves history *by conversation ID*
    history = await get_last_n_messages(session, conversation_id_uuid, n=10)


    # =========================================================
    # 3. LONG-TERM CONTEXT: mem0 retrieval (filters by app_id/user_id)
    # =========================================================
    # We can optionally filter mem0 by conversation_id if we store it there (see background task update)
    filters = {"AND": [{"user_id": user_id_str}, {"app_id": "awaren_ai"}]}
    memories = mem0.search(user_input, user_id=user_id_str, limit=5, filters=filters)
    context = "\n".join(m.get("memory", "") for m in memories) if memories else ""
    
    system_prompt = PromptRepo.chat_system(memories=context)


    # 4. Stream response and handle events
    async def event_generator():
        full_reply = ""
        
        try:
            # STREAMING PHASE
            async for chunk in chat_service.stream_generate(system_prompt, user_input, history=history): 
                full_reply += chunk
                yield {
                    "event": "message",
                    "data": json.dumps({"chunk": chunk})
                }

            # FINAL EVENT YIELDED IMMEDIATELY 
            yield {
                "event": "done",
                "data": json.dumps({
                    "conversation_id": str(conversation_id_uuid), # <-- RETURN THE ID TO THE FRONTEND
                    "is_new": is_new_conversation,
                    "memories": memories,
                })
            }
            
            # STORAGE PHASE (DECOUPLED)
            background_tasks.add_task(
                persist_chat_data,
                user_id_uuid,
                conversation_id_uuid,
                user_id_str,
                user_input,
                full_reply.strip()
            )

            if is_new_conversation:
                background_tasks.add_task(
                    generate_and_store_title,
                    conversation_id_uuid,
                    user_id_uuid,
                    user_input
                )




        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }       

    return EventSourceResponse(event_generator())

# app/api/v1/chat_routes.py (NEW FUNCTION)

# NOTE: This function needs to be outside of the chat_stream scope if it's using BackgroundTasks.
# However, since it needs the AsyncSession, we must handle the session lifecycle carefully.
# The cleanest way is to pass the data, and let a service handle the session opening/closing.

# --- BACKGROUND PERSISTENCE FUNCTION ---
# This function is now responsible for COMMITTING the transaction.

async def persist_chat_data(
    user_id_uuid: UUID,
    conversation_id: UUID,
    user_id_str: str,
    user_input: str,
    full_reply: str
):
    """Performs all persistence (DB History and mem0) in the background."""

    # -----------------------------
    # 1. DATABASE PERSISTENCE
    # -----------------------------
    try:
        async with AsyncSessionLocal() as session:
            await add_message_to_history(
                session,
                user_id_uuid,
                conversation_id,
                "user",
                user_input,
            )
            await add_message_to_history(
                session,
                user_id_uuid,
                conversation_id,
                "assistant",
                full_reply,
            )
            await session.commit()

    except Exception as e:
        # No rollback outside session context
        print(
            f"ERROR: Background DB storage failed. "
            f"Conversation ID: {conversation_id} Error: {e}"
        )

    # -----------------------------
    # 2. MEM0 PERSISTENCE
    # -----------------------------
    try:
        mem0.add(
            [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": full_reply},
            ],
            user_id=user_id_str,
            metadata={
                "app_id": "awaren_ai",
                "conversation_id": str(conversation_id),
            },
        )
    except Exception as e:
        print(f"ERROR: Background mem0 storage failed. Error: {e}")


# NOTE: Due to how BackgroundTasks and dependencies work, it's often cleaner to
# pass a dedicated session/connection object to the background task, rather than the 
# one tied to the main request, but we will use the current dependency setup for simplicity.
# For production, consider moving the session creation into the background function itself
# using a dedicated connection manager.