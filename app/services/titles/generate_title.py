import logger
from app.services.llm.bed_rock import BedrockLLM
from app.repo.prompt_repo import PromptRepo
from app.db.db import AsyncSession, AsyncSessionLocal
from app.models.chat import Conversation
from uuid import UUID
from app.services.cache.redis_manager import CacheManager
from sqlalchemy import select

async def call_nova_for_title(prompt_text: str) -> str:
    """
    Uses Amazon Nova to generate a creative 3-word title.
    """
    try:
        llm = BedrockLLM(
            model_id="amazon.nova-lite-v1:0",
            temperature=0.4,
        )

        prompt = PromptRepo.title_from_first_message(prompt_text)

        return await llm.invoke(prompt)

    except Exception as e:
        print(f"Error generating title: {e}")
        return "New Insight"


async def update_conversation_title(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    new_title: str,
):
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation:
        conversation.title = new_title
        return conversation

    return None

async def generate_and_store_title(
    conversation_id: UUID,
    user_id: UUID,
    first_message: str,
):
    try:
        title = await call_nova_for_title(first_message)

        async with AsyncSessionLocal() as session:
            await update_conversation_title(
                session,
                conversation_id,
                user_id,
                title
            )
            await session.commit()

        # ❌ DO NOT invalidate sidebar cache here

    except Exception as e:
        logger.exception(
            f"Title generation failed for conversation {conversation_id}"
        )

