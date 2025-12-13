import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.db import Base
from pydantic import EmailStr, BaseModel

class User(Base):
    __tablename__ = "users"
    # store UUID natively in Postgres, returned as uuid.UUID by SQLAlchemy
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)

class UserCreate(BaseModel):
    user_name: str
    email: EmailStr
    password: str