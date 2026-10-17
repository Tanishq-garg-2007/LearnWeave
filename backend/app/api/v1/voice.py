import asyncio
import logging
from typing import Optional, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from app.db.models import User
from app.api.deps import get_current_user
from app.api.error_utils import internal_error, new_error_reference
from app.services.document_service import DocumentError, read_upload_limited
from app.services.tts_service import tts_service
from app.services.groq_client import groq_client, GroqClientError

logger = logging.getLogger("learnweave.api.voice")
from app.api.rate_limit import limit_by_ip, limit_by_user

router = APIRouter(prefix="/voice", tags=["Voice Pipeline (TTS & STT)"])


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Literal["af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "am_adam", "am_michael", "bf_emma", "bm_george"] = "af_heart"
    speed: float = Field(1.0, ge=0.5, le=2.0)


class TranscribeResponse(BaseModel):
    text: str


@router.post("/speak", dependencies=[Depends(limit_by_user('tts', 20, 60))])
async def text_to_speech(
    req: SpeakRequest,
    user: User = Depends(get_current_user)
):
    """
    Synthesize speech audio from text using local Kokoro-82M ONNX or 24kHz PCM WAV engine.
    Returns 24kHz 16-bit mono WAV audio stream.
    """
    clean_text = req.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text for speech synthesis cannot be empty"
        )

    # Limit text to 2000 chars per speech synthesis call for latency & stability
    if len(clean_text) > 2000:
        clean_text = clean_text[:2000]

    # Synthesis is a CPU-bound Python loop; run it in a worker thread so other requests keep being served.
    wav_bytes, gen_time, engine = await asyncio.to_thread(
        tts_service.synthesize_wav,
        text=clean_text,
        voice=req.voice or "af_heart",
        speed=req.speed or 1.0
    )

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "inline; filename=\"speech.wav\"",
            "X-Audio-Engine": engine,
            "X-Generation-Time": f"{gen_time:.3f}s"
        }
    )


@router.post("/listen", response_model=TranscribeResponse, dependencies=[Depends(limit_by_user('stt', 10, 60, llm=True))])
async def speech_to_text(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Transcribe spoken student query or doubt using Groq whisper-large-v3-turbo.
    """
    try:
        audio_bytes = await read_upload_limited(file)
    except DocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message)

    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty"
        )

    filename = file.filename or "audio.wav"
    try:
        transcription = await groq_client.transcribe_audio(audio_bytes=audio_bytes, filename=filename)
        return TranscribeResponse(text=transcription)
    except GroqClientError as exc:
        # Upstream status codes are not forwarded: a Groq 401 is our configuration problem, not the caller's.
        ref = new_error_reference()
        logger.error(f"[ref={ref}] Groq Whisper transcription failed (upstream status={exc.status_code}): {exc}")
        code = status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(
            status_code=code,
            detail=f"Speech transcription is temporarily unavailable. Please try again. (reference: {ref})"
        )
    except Exception as exc:
        raise internal_error(logger, exc, "Failed to transcribe audio")
