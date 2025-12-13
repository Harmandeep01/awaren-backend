from fastapi import APIRouter, HTTPException, status
import json
from fastapi import Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import auth 
from app.schema import chat_schema
from app.services import mem0_service

router = APIRouter(prefix="/memory")

# --- Endpoint for UI to preview relevant memories (non-streaming) ---
@router.get("/relevant", response_model=list[chat_schema.MemoryItem])
async def get_relevant_memories(q: str, current_user = Depends(auth.get_current_user)):
    user_id_str = str(current_user.user_id)
    filters = {"AND": [{"user_id": user_id_str}, {"app_id": "health_bot"}]}
    memories = mem0_service.mem0.search(q, user_id=user_id_str, limit=10, filters=filters)
    # Normalize output (ensure each item has memory and score)
    out = []
    for m in memories:
        out.append({"memory": m.get("memory") or m.get("content"), "score": m.get("score", 0.0)})
    return out