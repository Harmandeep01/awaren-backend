import asyncio
import json
from typing import AsyncGenerator, List, Dict
from app.services.memory.mem0_service import mem0
from app.config.settings import settings
# Swapping to AWS Bedrock
from langchain_aws import ChatBedrock
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks import AsyncCallbackHandler

class QueueCallbackHandler(AsyncCallbackHandler):
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def on_llm_new_token(self, token, **kwargs) -> None:
        if isinstance(token, list):
            token = "".join(part.get("text", "") for part in token)
        await self.queue.put(str(token))


async def stream_generate(
    system_prompt: str,
    user_input: str,
    history: List[Dict] = None,
) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    callback = QueueCallbackHandler(queue)

    llm = ChatBedrock(
        model_id="amazon.nova-lite-v1:0", 
        streaming=True,
        callbacks=[callback],
        region_name=settings.aws_region, # Ensure region_name is used
        model_kwargs={"temperature": 0.4}
    )

    # Nova Lite expects content as a list of dictionaries
    messages = [SystemMessage(content=[{"text": system_prompt}])]
    
    if history:
        for turn in history:
            role = turn.get("role")
            content = turn.get("content")
            # If content is already a string, wrap it for Nova
            formatted_content = [{"text": content}] if isinstance(content, str) else content
            
            if role == "user":
                messages.append(HumanMessage(content=formatted_content))
            elif role == "assistant":
                messages.append(AIMessage(content=formatted_content))
    
    messages.append(HumanMessage(content=[{"text": user_input}]))

    async def run_llm():
        try:
            # invoke handles the Converse API formatting requirements
            await llm.ainvoke(messages)
        except Exception as e:
            await queue.put(f"[ERROR] {e}")
        finally:
            await queue.put(None)

    task = asyncio.create_task(run_llm())
    while True:
        token = await queue.get()
        if token is None:
            break
        yield token

    await task



async def get_insights_from_nova(user_id: str):
    """
    Step 1: Fetch memories using the required user_id filter.
    Step 2: Analyze with Amazon Nova.
    """
    try:
        # satisfy the Mem0 API requirement for user_id
        memories =   mem0.client.search(
            query="What are my recent mindset shifts and goals?",
            filters={
                "AND": [
                    {"user_id": user_id}, # This fixes your error
                    {"categories": {"contains": "behaviour"}}
                ]
            },
            rerank=True, # Optimal for Nova analysis
            limit=10
        )

        if not memories:
            return {"title": "Fragmenting...", "description": "Not enough neural data yet.", "badge": "SYNCING"}

        # Convert list of memories to a clean string context
        context = "\n".join([m['memory'] for m in memories])
        
        # Pass to your existing analysis function
        return await analyze_life_patterns(context)
        
    except Exception as e:
        print(f"Retrieval Error: {e}")
        return {"error": str(e)}

async def analyze_life_patterns(memory_context: str):
    """
    Deep Behavioral Analysis using Nova Lite
    """
    llm = ChatBedrock(
        model_id="amazon.nova-lite-v1:0",
        region=settings.aws_region,
        model_kwargs={"temperature": 0.4}
    )
    
    prompt = f"""
    Analyze these user memories to find a deep psychological pattern.
    Focus on the shift from old habits to new goals.
    Generate a relevant Title , Description and badge
    Memories: {memory_context}
    
    Return ONLY JSON: 
    {{ "title": "2-word title", "description": "30-word summary", "badge": "CATEGORY" }}
    """
    
    response = await llm.ainvoke(prompt)
    clean_content = response.content.replace('```json', '').replace('```', '').strip()
    print(f"Cleaned content: {clean_content}")
    return json.loads(clean_content)