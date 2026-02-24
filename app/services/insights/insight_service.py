import json
from typing import Dict, List

from app.services.memory.mem0_service import mem0
from app.services.llm.bed_rock import BedrockLLM
from app.repo.prompt_repo import PromptRepo


class InsightService:
    """
    Owns all Insight-related use cases.
    No FastAPI, no routing, no auth.
    """

    def __init__(self):
        self.llm = BedrockLLM(
            model_id="amazon.nova-lite-v1:0",
            temperature=0.4
        )

    # -----------------------------
    # HERO INSIGHT
    # -----------------------------
    async def get_hero_insight(self, user_id: str) -> Dict:
        """
        High-level psychological insight based on long-term memory.
        """

        memories = mem0.client.search(
            query="What are my primary mindset shifts and goal progress?",
            user_id=user_id,
            rerank=True,
            limit=10,
        )

        if not memories:
            return {
                "title": "Quiet Mind",
                "description": "AWAREN is waiting for more reflections to identify a distinct pattern.",
                "badge": "ANALYZING",
            }

        context = "\n".join(m["memory"] for m in memories if m.get("memory"))
        return await self._analyze_patterns(context)

    # -----------------------------
    # DATA INSIGHTS
    # -----------------------------
    async def get_data_insights(self, user_id: str) -> Dict:
        """
        Structured, non-LLM insights pulled directly from memory.
        """
        

        raw_prefs = mem0.client.search(
            query=PromptRepo.insight_memory_queries()["preferences"],
            user_id=user_id,   # ✅ REQUIRED HERE
            filters={
                "categories": {"contains": "preferences"}
            },
            limit=5,
        )

        # Optional safety pass (fine to keep)
        preferences = [
            p for p in raw_prefs
            if "preferences" in (p.get("categories") or [])
        ]

        rhythm = mem0.client.search(
        query=PromptRepo.insight_memory_queries()["hero"],
        user_id=user_id,   # ✅ REQUIRED HERE
        filters={
            "categories": {"contains": "behaviour"}
        },
        rerank=True,
        limit=4,
    )

        return {
            "preferences": preferences,
            "rhythm": rhythm,
        }

    # -----------------------------
    # INTERNAL: LLM ANALYSIS
    # -----------------------------
    async def _analyze_patterns(self, memory_context: str) -> Dict:
        """
        Nova-powered psychological pattern extraction.
        """

        prompt = PromptRepo.hero_insight(memory_context=memory_context)

        raw = await self.llm.invoke(prompt)

        # Defensive JSON parsing (kept identical to previous behavior)
        
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    

    # -----------------------------
    # INTERNAL: DEEP EXPLORATION
    # -----------------------------
    async def explore_deep_insights(self, user_id: str) -> Dict:
        """
        Nova-powered psychological pattern extraction.
        """

        deep_memories = mem0.client.search(
        query="Analyze the transition from my old habits to my new intentional lifestyle",
        user_id=user_id,
        filters={"AND": [{"user_id": user_id}, {"categories": {"contains": "behaviour"}}]},
        rerank=True, 
        limit=15 # Higher limit for deeper LLM context
    )
        print(f"Deep meories: {deep_memories}")
        prompt = PromptRepo.deep_insights(memory_context=deep_memories)

        try:
            response = await self.llm.invoke(prompt)
            print(f"Response: {response}")
            # Cleaning the response for JSON parsing
            clean = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        
        except Exception as e:
            return {
                "modal_title": "Evolution Sync",
                "evolution_summary": "Your neural patterns are currently realigning.",
                "pattern_recognition": "AWAREN is waiting for more consistent data points to finalize this recognition.",
                "reflection_question": "What does clarity feel like to you right now?"
            }
