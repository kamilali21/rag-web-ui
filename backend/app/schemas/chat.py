from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class MessageBase(BaseModel):
    content: str
    role: str

class MessageCreate(MessageBase):
    chat_id: int

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)

class ChatCreate(ChatBase):
    knowledge_base_ids: List[int] | None = Field(default=None, max_length=100)
    source_scope: Literal["public", "private", "both"] = "private"

class ChatUpdate(ChatBase):
    knowledge_base_ids: Optional[List[int]] = None

class ChatResponse(ChatBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    knowledge_base_ids: List[int] = []
    source_scope: Literal["public", "private", "both"] = "private"

    class Config:
        from_attributes = True
