from fastapi import APIRouter, Depends, Query

from app.config import auth
from app.services.insights.insight_service import InsightService
from app.services.cache.redis_manager import CacheManager
router = APIRouter(prefix="/insights")

service = InsightService()


DEFAULT_TTL = 3600  # 1 hour


# -----------------------------
# HERO INSIGHT
# -----------------------------
@router.get("/hero")
async def get_hero_insight(
    refresh: bool = Query(False),
    current_user=Depends(auth.get_current_user),
):
    user_id = str(current_user.user_id)
    cache_key = f"insights:hero:{user_id}"

    if not refresh:
        cached = await CacheManager.get(cache_key)
        if cached:
            return cached

    data = await service.get_hero_insight(user_id=user_id)

    await CacheManager.set(cache_key, data, expire=DEFAULT_TTL)
    return data


# -----------------------------
# DATA INSIGHTS
# -----------------------------
@router.get("/data")
async def get_data_insights(
    refresh: bool = Query(False),
    current_user=Depends(auth.get_current_user),
):
    user_id = str(current_user.user_id)
    cache_key = f"insights:data:{user_id}"

    if not refresh:
        cached = await CacheManager.get(cache_key)
        if cached:
            return cached

    data = await service.get_data_insights(user_id=user_id)

    await CacheManager.set(cache_key, data, expire=DEFAULT_TTL)
    return data


# -----------------------------
# DEEP INSIGHTS
# -----------------------------
@router.get("/explore")
async def get_deep_insights(
    refresh: bool = Query(False),
    current_user=Depends(auth.get_current_user),
):
    user_id = str(current_user.user_id)
    cache_key = f"insights:deep:{user_id}"

    if not refresh:
        cached = await CacheManager.get(cache_key)
        if cached:
            return cached

    data = await service.explore_deep_insights(user_id=user_id)

    await CacheManager.set(cache_key, data, expire=DEFAULT_TTL)
    return data