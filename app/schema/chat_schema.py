from pydantic import BaseModel, EmailStr
from typing import Optional, List

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChatRequest(BaseModel):
    text: str

class MemoryItem(BaseModel):
    id: str
    memory: str
    score: float = 0.0
    categories: List[str] = []
