import asyncio
from typing import AsyncGenerator, List, Dict, Optional

from app.config.settings import settings

from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks import AsyncCallbackHandler


# ==============================
# Internal: Streaming Queue Handler
# ==============================
class _QueueCallbackHandler(AsyncCallbackHandler):
    """
    Normalizes Bedrock / Nova streaming tokens.
    Nova may emit structured content blocks instead of strings.
    """

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def on_llm_new_token(self, token, **kwargs) -> None:
        # Nova can emit: [{"text": "..."}]
        if isinstance(token, list):
            token = "".join(part.get("text", "") for part in token)
        await self.queue.put(str(token))


# ==============================
# Bedrock LLM Client
# ==============================
class BedrockLLM:
    """
    Thin, prompt-agnostic wrapper around Amazon Bedrock (Nova).
    Responsibilities:
    - Handle streaming
    - Normalize content formats
    - Hide LangChain / Nova quirks
    """

    def __init__(
        self,
        model_id: str = "amazon.nova-lite-v1:0",
        temperature: float = 0.4,
        region_name: Optional[str] = None,
    ):
        self.model_id = model_id
        self.temperature = temperature
        self.region_name = region_name or settings.aws_region

    # ------------------------------
    # Streaming Invoke
    # ------------------------------
    async def stream(
        self,
        system_prompt: str,
        user_input: str,
        history: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams tokens from Bedrock.
        Yields ONLY strings (safe for SSE concatenation).
        """

        queue: asyncio.Queue[str | None] = asyncio.Queue()
        callback = _QueueCallbackHandler(queue)

        llm = ChatBedrock(
            model_id=self.model_id,
            streaming=True,
            callbacks=[callback],
            region_name=self.region_name,
            model_kwargs={"temperature": self.temperature},
        )

        # Nova expects content as list[{"text": "..."}]
        messages = [SystemMessage(content=[{"text": system_prompt}])]

        if history:
            for turn in history:
                role = turn.get("role")
                content = turn.get("content")

                formatted = (
                    [{"text": content}]
                    if isinstance(content, str)
                    else content
                )

                if role == "user":
                    messages.append(HumanMessage(content=formatted))
                elif role == "assistant":
                    messages.append(AIMessage(content=formatted))

        messages.append(HumanMessage(content=[{"text": user_input}]))

        async def _run():
            try:
                await llm.ainvoke(messages)
            except Exception as e:
                await queue.put(f"[ERROR] {e}")
            finally:
                await queue.put(None)

        task = asyncio.create_task(_run())

        while True:
            token = await queue.get()
            if token is None:
                break
            yield token

        await task

    # ------------------------------
    # Non-Streaming Invoke
    # ------------------------------
    async def invoke(
        self,
        prompt: str,
    ) -> str:
        """
        Non-streaming call.
        Always returns a clean string.
        """

        llm = ChatBedrock(
            model_id=self.model_id,
            region_name=self.region_name,
            model_kwargs={"temperature": self.temperature},
        )

        response = await llm.ainvoke(prompt)

        content = response.content
        if isinstance(content, list):
            content = "".join(c.get("text", "") for c in content)

        return str(content).strip()