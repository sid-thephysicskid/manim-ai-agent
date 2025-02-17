from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class JobSubmission(BaseModel):
    question: str = Field(..., description="The question or lesson topic for the video.")
    rendering_quality: str = Field("medium", description="Rendering quality (e.g., low, medium, high)")
    duration_detail: str = Field("normal", description="Descriptor for video detail/duration")
    user_level: str = Field(..., description="User knowledge level (e.g., child, high_school, college)")
    voice_model: str = Field("nova", description="Preferred voice model for voiceover")
    email: Optional[EmailStr] = Field(None, description="Email address to send notifications") 