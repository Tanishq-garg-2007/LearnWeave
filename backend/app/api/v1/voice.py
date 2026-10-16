import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from app.db.models import User
from app.api.deps import get_current_user
from app.services.tts_service import tts_service
from app.services.groq_client import groq_client, GroqClientError

logger = logging.getLogger("learnweave.api.voice")
router = APIRouter(prefix="/voice", tags=["Voice Pipeline (TTS & STT)"])


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = "af_heart"
    speed: Optional[float] = 1.0


class TranscribeResponse(BaseModel):
    text: str


@router.post("/speak")
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

    wav_bytes, gen_time, engine = tts_service.synthesize_wav(
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


@router.post("/listen", response_model=TranscribeResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Transcribe spoken student query or doubt using Groq whisper-large-v3-turbo.
    """
    audio_bytes = await file.read()
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty"
        )

    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file exceeds 25MB limit"
        )

    filename = file.filename or "audio.wav"
    try:
        transcription = await groq_client.transcribe_audio(audio_bytes=audio_bytes, filename=filename)
        return TranscribeResponse(text=transcription)
    except GroqClientError as exc:
        logger.error(f"Groq Whisper transcription failed: {exc}")
        raise HTTPException(status_code=exc.status_code or 503, detail=str(exc))
    except Exception as exc:
        logger.error(f"Audio transcription error: {exc}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to transcribe audio")
