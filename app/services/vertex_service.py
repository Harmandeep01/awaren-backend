import asyncio
from typing import AsyncGenerator

from app.config.settings import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks import AsyncCallbackHandler


class QueueCallbackHandler(AsyncCallbackHandler):
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        await self.queue.put(token)


async def stream_generate(
    system_prompt: str,
    user_input: str
) -> AsyncGenerator[str, None]:

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    callback = QueueCallbackHandler(queue)

    llm = ChatGoogleGenerativeAI(
        model=settings.vertex_model_name,   # gemini-2.5-flash
        temperature=0.4,
        streaming=True,
        callbacks=[callback],
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input),
    ]

    async def run_llm():
        try:
            await llm.ainvoke(messages)
        except Exception as e:
            await queue.put(f"[ERROR] {e}")
        finally:
            await queue.put(None)

    task = asyncio.create_task(run_llm())
    while True:
        token = await queue.get()
        print(f"Tokens: {token}")
        if token is None:
            break
        yield token

    await task
