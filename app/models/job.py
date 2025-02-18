from enum import Enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self):
        return self.value

class Job(BaseModel):
    """Job model for storing workflow state and metadata."""
    job_id: str
    question: str
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_stage: str = Field(default="plan")
    logs: List[str] = Field(default_factory=list)
    result_url: Optional[str] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            JobStatus: lambda v: v.value,
            datetime: lambda v: v.isoformat()
        } 