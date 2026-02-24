# app/db/models.py

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# Import your existing declarative base from app/db/db
# If your Base is defined differently, adjust this import.
from app.db.db import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.user_id"), 
        nullable=False, 
        index=True
    )
    title = Column(String(255), nullable=True) # Will be generated later
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationship to ChatHistory
    messages = relationship("ChatHistory", back_populates="conversation", order_by="ChatHistory.timestamp")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key to the User table
    # Assumes your 'users' table uses UUID for the user_id column
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.user_id"), 
        nullable=False, 
        index=True
    )
    
    # Role: 'user' or 'assistant' (varchar(10))
    role = Column(String(10), nullable=False)
    
    # Content: The message text
    content = Column(Text, nullable=False)
    
    # Timestamp: Used for chronological ordering
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Optional: Relationship back to the User model, if defined
    # user = relationship("User", back_populates="chat_messages") 
    conversation_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("conversations.id"), 
        nullable=False, 
        index=True
    )
    
    # Relationship back to the Conversation model
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<ChatHistory(user_id='{self.user_id}', role='{self.role}', content='{self.content[:30]}...')>"