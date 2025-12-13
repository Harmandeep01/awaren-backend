from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config.settings import settings
from app.db.db import get_session
from app.models.user import User
import uuid
import bcrypt
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _normalize_secret(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        _normalize_secret(password),
        hashed.encode()
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        _normalize_secret(password),
        bcrypt.gensalt()
    ).decode()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        # Convert token-sub (string) to UUID object for querying
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        # ValueError covers invalid UUID strings
        raise credentials_exception

    # Fetch user from DB (user_id is UUID type in model)
    q = await session.execute(select(User).where(User.user_id== user_id))
    user = q.scalars().first()
    if user is None:
        raise credentials_exception
    return user