from fastapi import APIRouter, HTTPException
import json
from fastapi import Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import auth 
from app.db.db import get_session
from app.services import mem0_service
from app.services import vertex_service

router = APIRouter(prefix="/chat")

# --- Chat streaming endpoint ---
@router.post("/stream")
async def chat_stream(request: Request, session: AsyncSession = Depends(get_session), current_user = Depends(auth.get_current_user)):
    payload = await request.json()
    user_input = payload.get("text", "")
    if not user_input:
        raise HTTPException(status_code=400, detail="No text provided")

    # user id from current_user (SQLAlchemy model) is a UUID object; convert to str for mem0
    user_id_str = str(current_user.user_id)
    print(f"Current user id: {user_id_str}")
    # 1. Search mem0
    filters = {"AND": [{"user_id": user_id_str}, {"app_id": "health_bot"}]}
    memories = mem0_service.mem0.search(user_input, user_id=user_id_str, limit=5, filters=filters)
    context = "\n".join(m.get("memory", "") for m in memories) if memories else ""
    system_prompt = f"You're Ray, a running coach. Reply in one short paragraph only. No rambling. Here are past memories:\n{context}" if context else "You're Ray, a running coach. Reply in one short paragraph only. No rambling."

    # 2. Stream response using vertex_client.stream_generate()
    async def event_generator():
        full_reply = ""  # <--- Capture the full streamed LLM response

        try:
            async for chunk in vertex_service.stream_generate(system_prompt, user_input): 
                print(f"Chunk printing: {chunk}")   
                full_reply += chunk  # accumulate actual response
                yield {
                    "event": "message",
                    "data": json.dumps({"chunk": chunk})
                }

            # Final event -> send relevant memories
            print(f"Full reply :{full_reply}")
            yield {
                "event": "done",
                "data": json.dumps({"memories": memories})
            }

            # 3. Store REAL LLM output in mem0
            try:
                mem0_service.mem0.add(
                    [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": full_reply.strip()}  # real human reply
                    ],
                    user_id=user_id_str,
                    metadata={"app_id": "health_bot"}
                )
            except Exception:
                pass

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())