from fastapi import FastAPI
from app.db.db import engine, Base

# routes
from app.api.v1.chat_routes import router as chat_routes
from app.api.v1.user_routes import router as user_routes
from app.api.v1.memory_routes import router as memory_routes
# Create DB tables on startup (for demo; in prod use migrations)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app = FastAPI(title="Health Bot (Vertex+mem0) - Streaming demo")

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(chat_routes, prefix="/api/v1")
app.include_router(user_routes, prefix="/api/v1")
app.include_router(memory_routes, prefix="/api/v1")