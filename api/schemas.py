from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class MessageCreate(BaseModel):
    content: str

class MessageRead(BaseModel):
    id: int
    sender: str
    content: str
    timestamp: datetime
    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    title: Optional[str] = "Untitled"

class ConversationRead(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[MessageRead] = []
    class Config:
        from_attributes = True
