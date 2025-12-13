from fastapi import APIRouter, HTTPException, status
import json
from fastapi import Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import auth 
from app.db.db import get_session
from app.models.user import User, UserCreate
from app.schema import chat_schema

router = APIRouter(prefix="/user")

@router.post("/auth/register", response_model=chat_schema.Token)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    # check existing
    q = await session.execute(select(User).where(User.email == user.email))
    existing = q.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    print(f"Password received: {user.password}")
    hashed = auth.get_password_hash(user.password)
    new = User(user_name=user.user_name, email=user.email, hashed_password=hashed)
    session.add(new)
    await session.commit()
    await session.refresh(new)
    # token must contain string representation of UUID
    access_token = auth.create_access_token(data={"sub": str(new.user_id), "user_name" : str(new.user_name)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=chat_schema.Token)
async def login(form_data: Request, session: AsyncSession = Depends(get_session)):
    data = await form_data.json()
    email = data.get("email")
    password = data.get("password")
    q = await session.execute(select(User).where(User.email == email))
    user = q.scalars().first()
    if not user or not auth.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth.create_access_token(data={"sub": str(user.user_id), "user_name": str(user.user_name)})
    return {"access_token": token, "token_type": "bearer"}