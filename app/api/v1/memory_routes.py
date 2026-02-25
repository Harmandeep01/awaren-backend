from fastapi import APIRouter, HTTPException, status, Query
import json
from fastapi import Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import auth 
from app.schema import chat_schema
from app.services.memory import mem0_service
from app.services.chat.chat_service import analyze_life_patterns
from app.services.cache.redis_manager import CacheManager

router = APIRouter(prefix="/memory")

# --- Endpoint for UI to preview relevant memories (non-streaming) ---
@router.get("/relevant", response_model=list[chat_schema.MemoryItem])
async def get_relevant_memories(
    q: str,
    current_user = Depends(auth.get_current_user)
):
    user_id_str = str(current_user.user_id)
    filters = {"AND": [{"user_id": user_id_str}, {"app_id": "health_bot"}]}

    memories = mem0_service.mem0.search(
        q,
        user_id=user_id_str,
        limit=10,
        filters=filters
    )

    out = []
    for m in memories:
        out.append({
            "memory": m.get("memory") or m.get("content"),
            "score": m.get("score", 0.0),
            "categories": m.get("categories", []) or []
        })

    return out

@router.get("/all", response_model=list[chat_schema.MemoryItem])
async def get_all_memories(
    refresh: bool = Query(False),
    limit: int = 20,
    current_user=Depends(auth.get_current_user),
):
    user_id = str(current_user.user_id)
    cache_key = f"memories:all:{user_id}"
    
    # 1️⃣ If refresh is requested, KILL the old cache immediately
    if refresh:
        await CacheManager.delete(cache_key) 
    else:
        # Standard flow: return from cache if it exists
        cached = await CacheManager.get(cache_key)
        if cached:
            return cached[:limit]

    # 2️⃣ Source of truth (mem0) - Bypass phase
    # Note: Ensure Render has AWS credentials to avoid the error you saw
    memories = mem0_service.mem0.client.get_all(user_id=user_id)
    
    out = []
    for m in memories:
        # ... (Normalization logic remains the same)
        raw_categories = m.get("categories", []) or []
        clean_categories = [
            cat.split(":")[-1].strip().capitalize() if ":" in cat else cat.capitalize()
            for cat in raw_categories
        ]

        out.append({
            "id": m.get("id"),
            "memory": m.get("memory") or m.get("content"),
            "score": m.get("score", 1.0),
            "categories": clean_categories or ["Fragment"],
        })

    # 3️⃣ ALWAYS update or clear the cache for future requests
    # Even if 'out' is empty, we set it so Redis reflects the current empty state
    await CacheManager.set(cache_key, out, expire=3600)
    
    return out[:limit]

@router.get("/{memory_id}")
async def get_memory_by_id(
    memory_id: str,
    current_user = Depends(auth.get_current_user),
):
    user_id_str = str(current_user.user_id)

    memory = mem0_service.mem0.client.get(
        memory_id=memory_id,
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Return exactly what Mem0 returns
    return memory

@router.delete("/delete-all-by-user")
async def delete_all_memories(
    current_user = Depends(auth.get_current_user),
):
    user_id_str = str(current_user.user_id)
    memory = mem0_service.mem0.client.delete_all(
        user_id='90266b83-0f31-4101-a8fa-bac7aa7588af'
        # app_id='health_bot'
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    # Return exactly what Mem0 returns
    return memory


# # --- ROUTE 1: THE HERO INSIGHT (LLM POWERED) ---
# @router.get("/insights/hero")
# async def get_hero_insight(current_user = Depends(auth.get_current_user)):
#     user_id_str = str(current_user.user_id)
    
#     # Advanced Retrieval: satisfy the Mem0 filter and use Reranking for LLM context
#     memories = mem0_service.mem0.client.search(
#         query="What are my primary mindset shifts and goal progress?",
#         user_id=user_id_str,
#         rerank=True, 
#         limit=10
#     )
    
#     # Check for empty memories to avoid LLM hallucination
#     if not memories:
#         return {
#             "title": "Quiet Mind",
#             "description": "AWAREN is waiting for more reflections to identify a distinct pattern.",
#             "badge": "ANALYZING"
#         }

#     context = "\n".join([m['memory'] for m in memories])
#     # Passes the context to your Amazon Nova Lite analyzer
#     return await analyze_life_patterns(context)

# # --- ROUTE 2: DATA-DRIVEN BLOCKS (MEM0 SEARCH) ---
# # --- DATA-DRIVEN BLOCKS (STRICT FILTERING) ---
# @router.get("/insights/data")
# async def get_insight_data(current_user=Depends(auth.get_current_user)):
#     user_id_str = str(current_user.user_id)

#     # 1. STRICT PREFERENCES
#     raw_prefs = mem0_service.mem0.client.search(
#         query="What are my specific lifestyle and dietary preferences?",
#         user_id=user_id_str,   # ✅ REQUIRED HERE
#         filters={
#             "categories": {"contains": "preferences"}
#         },
#         limit=5,
#     )

#     # Optional safety pass (fine to keep)
#     prefs = [
#         p for p in raw_prefs
#         if "preferences" in (p.get("categories") or [])
#     ]

#     # 2. BEHAVIORAL RHYTHM
#     raw_rhythm = mem0_service.mem0.client.search(
#         query="What are my daily recurring habits and routines?",
#         user_id=user_id_str,   # ✅ REQUIRED HERE
#         filters={
#             "categories": {"contains": "behaviour"}
#         },
#         rerank=True,
#         limit=4,
#     )

#     return {
#         "preferences": prefs,
#         "rhythm": raw_rhythm,
#     }
