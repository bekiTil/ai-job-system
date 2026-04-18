from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field

ALLOWED_TASK_TYPES = {"summarize", "classify", "extract"}

class UserCreate(BaseModel):
    email: str = Field(..., description="User email")
    name: str = Field(..., min_length=1, max_length=255)


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}

class JobCreate(BaseModel):
    user_id: UUID = Field(..., description="ID of the user submitting the job")
    task_type: str = Field(..., description="One of: summarize, classify, extract")
    input_text: str = Field(..., min_length=1, max_length=10000)


class JobResponse(BaseModel):
    id: UUID
    user_id: UUID
    task_type: str
    status: str
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    failed_reason: Optional[str] = None
    priority: int = 0

    model_config = {"from_attributes": True}