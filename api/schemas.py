from pydantic import BaseModel, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime

# ------------------------
# User Schemas
# ------------------------




# ------------------------
# Message Schemas
# ------------------------

class MessageCreate(BaseModel):
    content: str

class MessageRead(BaseModel):
    id: int
    content: str
    sender: str  # "user" or "assistant"
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# ------------------------
# Conversation Schemas
# ------------------------

class ConversationCreate(BaseModel):
    pass

class ConversationRead(BaseModel):
    id: int
    created_at: datetime
    messages: List[MessageRead] = []
    model_config = ConfigDict(from_attributes=True)

# ------------------------
# Document Schemas
# ------------------------

class DocumentRead(BaseModel):
    id: int
    conversation_id: int
    doc_type: str
    content: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DocumentEditRequest(BaseModel):
    instruction: str  # e.g., "Add clause for arbitration"

# ------------------------
# Token Response
# ------------------------

class TokenOut(BaseModel):
    access_token: str
    token_type: str
    model_config = ConfigDict(from_attributes=True)
