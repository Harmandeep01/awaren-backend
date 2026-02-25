from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.db import engine, Base
import os
import tempfile
# routes
from app.api.v1.chat_routes import router as chat_routes
from app.api.v1.user_routes import router as user_routes
from app.api.v1.memory_routes import router as memory_routes
from app.api.v1.conversation_routes import router as conversation_routes
from app.api.v1.insight_routes import router as insight_routes
# Create DB tables on startup (for demo; in prod use migrations)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app = FastAPI(title="Health Bot (Vertex+mem0) - Streaming demo")

# Initialize Google Credentials from Environment Variable
google_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_json:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
        f.write(google_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name

# ---- Strict CORS Policy ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ONLY this origin is allowed
    allow_credentials=False,  # strict: disallow cookies / auth headers from browsers
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],  # explicit minimal allowed methods
    allow_headers=["*"],  # only the headers you actually need
)
# ----------------------------

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(chat_routes, prefix="/api/v1")
app.include_router(user_routes, prefix="/api/v1")
app.include_router(memory_routes, prefix="/api/v1")
app.include_router(conversation_routes, prefix="/api/v1")
app.include_router(insight_routes, prefix="/api/v1")

