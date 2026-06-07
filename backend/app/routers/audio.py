import logging
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ..model import analyze, transcribe, understand
from ..schemas import (
    AnalysisResponse,
    TranscriptionResponse,
    UnderstandResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_TYPES = {
    "audio/wav", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/ogg", "audio/x-ogg",
    "audio/flac", "audio/x-flac",
    "audio/webm",
    "audio/mp4", "audio/x-m4a",
    "audio/aac",
    "application/octet-stream",  # generic binary
}

MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB


def _validate_upload(file: UploadFile) -> None:
    if file.content_type not in SUPPORTED_TYPES:
        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in {"wav", "mp3", "ogg", "flac", "webm", "m4a", "aac"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported audio type: {file.content_type}",
            )


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    summary="Transcribe audio to text",
    description="Upload an audio file and receive its full transcription.",
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, FLAC, WebM, M4A)"),
) -> TranscriptionResponse:
    _validate_upload(audio)

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds 50 MB limit.",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = transcribe(audio_bytes, audio.filename or "audio.wav")
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return TranscriptionResponse(
        transcription=result["transcription"],
        filename=audio.filename or "audio.wav",
        duration_seconds=result.get("duration_seconds"),
    )


@router.post(
    "/understand",
    response_model=UnderstandResponse,
    summary="Answer a question about audio content",
    description=(
        "Upload an audio file along with a text question. "
        "The model will listen to the audio and answer your question."
    ),
)
async def understand_audio(
    audio: UploadFile = File(..., description="Audio file"),
    question: str = Form(
        default="What is this audio about?",
        description="Question to ask about the audio",
    ),
) -> UnderstandResponse:
    _validate_upload(audio)

    if not question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must not be empty.",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds 50 MB limit.",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        answer = understand(audio_bytes, audio.filename or "audio.wav", question)
    except Exception as exc:
        logger.exception("Audio understanding failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return UnderstandResponse(
        question=question,
        answer=answer,
        filename=audio.filename or "audio.wav",
    )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Comprehensive audio analysis",
    description=(
        "Upload an audio file to receive a full analysis: "
        "transcription, summary, and sentiment/tone assessment."
    ),
)
async def analyze_audio(
    audio: UploadFile = File(..., description="Audio file"),
) -> AnalysisResponse:
    _validate_upload(audio)

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds 50 MB limit.",
        )
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = analyze(audio_bytes, audio.filename or "audio.wav")
    except Exception as exc:
        logger.exception("Audio analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return AnalysisResponse(
        filename=audio.filename or "audio.wav",
        transcription=result["transcription"],
        summary=result["summary"],
        sentiment=result["sentiment"],
        duration_seconds=result.get("duration_seconds"),
    )
