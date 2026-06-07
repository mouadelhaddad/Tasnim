from pydantic import BaseModel, Field
from typing import Optional


class TranscriptionResponse(BaseModel):
    transcription: str
    filename: str
    duration_seconds: Optional[float] = None


class UnderstandRequest(BaseModel):
    question: str = Field(
        default="What is this audio about?",
        description="Question to ask about the audio content"
    )


class UnderstandResponse(BaseModel):
    question: str
    answer: str
    filename: str


class AnalysisResponse(BaseModel):
    filename: str
    transcription: str
    summary: str
    sentiment: str
    duration_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    device: str


class ErrorResponse(BaseModel):
    detail: str
