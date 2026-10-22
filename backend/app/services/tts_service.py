import base64
import io
import logging
import math
import struct
import time
import wave
from pathlib import Path
from typing import Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger("learnweave.tts")


class TTSService:
    """Centralized Text-to-Speech service with Kokoro-82M, Gemini hosted neural TTS, and WAV fallback."""

    def __init__(self):
        self._root = Path(__file__).resolve().parent.parent.parent.parent
        self._find_model_paths()
        self._kokoro = None
        self._initialized = False

    def _find_model_paths(self):
        candidates_model = [
            Path(settings.KOKORO_MODEL_PATH),
            self._root / settings.KOKORO_MODEL_PATH,
            self._root / "backend" / settings.KOKORO_MODEL_PATH,
        ]
        self.model_path = next((p for p in candidates_model if p.exists()), candidates_model[0])

        candidates_voices = [
            Path(settings.KOKORO_VOICES_PATH),
            self._root / settings.KOKORO_VOICES_PATH,
            self._root / "backend" / settings.KOKORO_VOICES_PATH,
        ]
        self.voices_path = next((p for p in candidates_voices if p.exists()), candidates_voices[0])

    def initialize_kokoro(self) -> Tuple[bool, float]:
        """Attempt to load Kokoro-82M ONNX model if weights exist locally. Returns (success, load_time_seconds)."""
        t0 = time.time()
        try:
            self._find_model_paths()
            if not self.model_path.exists() or not self.voices_path.exists():
                logger.info(f"Kokoro weights not found at {self.model_path}. Using hosted/standard synthesizer.")
                return False, time.time() - t0

            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro(str(self.model_path), str(self.voices_path))
            self._initialized = True
            load_time = time.time() - t0
            logger.info(f"Kokoro-82M loaded in {load_time:.3f}s from {self.model_path}")
            return True, load_time
        except Exception as exc:
            logger.warning(f"Kokoro-82M initialization skipped/failed: {exc}.")
            return False, time.time() - t0

    def _synthesize_gemini_tts(self, text: str, voice: str = "Puck") -> Optional[bytes]:
        """Synthesize speech using Google AI Studio / Gemini TTS API."""
        if not settings.GEMINI_API_KEY:
            return None

        model = settings.GEMINI_TTS_MODEL.strip()
        if not model.startswith("models/"):
            model = f"models/{model}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        # Map common voice preference to Gemini voices: Puck, Aoede, Charon, Fenrir, Kore
        gemini_voice = "Aoede" if "heart" in voice or "af" in voice else "Puck"

        payload = {
            "contents": [{"parts": [{"text": f"Read the following text aloud:\n{text.strip()}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": gemini_voice
                        }
                    }
                }
            }
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning(f"Gemini TTS API returned status {resp.status_code}: {resp.text[:200]}")
                    return None
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    inline = part.get("inlineData", {})
                    if "data" in inline:
                        raw_b64 = inline["data"]
                        pcm_bytes = base64.b64decode(raw_b64)
                        # Pack 24,000Hz 16-bit mono PCM into standard WAV
                        buf = io.BytesIO()
                        with wave.open(buf, "wb") as w:
                            w.setnchannels(1)
                            w.setsampwidth(2)
                            w.setframerate(24000)
                            w.writeframes(pcm_bytes)
                        return buf.getvalue()
        except Exception as exc:
            logger.warning(f"Gemini TTS generation failed: {exc}. Falling back to standard synthesizer.")
            return None
        return None

    def synthesize_wav(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[bytes, float, str]:
        """
        Synthesize text to WAV audio bytes.
        Returns: (wav_bytes, generation_time_seconds, engine_used)
        """
        t0 = time.time()

        # 1. If Kokoro engine is requested or auto-detected with local weights
        if settings.TTS_ENGINE in ("auto", "kokoro") and self.model_path.exists() and self.voices_path.exists():
            if not self._initialized:
                self.initialize_kokoro()
            if self._initialized and self._kokoro is not None:
                try:
                    samples, sample_rate = self._kokoro.create(text, voice=voice, speed=speed, lang="en-us")
                    import soundfile as sf
                    buf = io.BytesIO()
                    sf.write(buf, samples, sample_rate, format="WAV")
                    gen_time = time.time() - t0
                    return buf.getvalue(), gen_time, "kokoro-82m"
                except Exception as exc:
                    logger.warning(f"Kokoro synthesis failed: {exc}.")

        # 2. Try Gemini hosted neural TTS if GEMINI_API_KEY is available
        if settings.GEMINI_API_KEY and settings.TTS_ENGINE in ("auto", "gemini"):
            gemini_wav = self._synthesize_gemini_tts(text, voice=voice)
            if gemini_wav:
                gen_time = time.time() - t0
                return gemini_wav, gen_time, "gemini-flash-tts"

        # 3. Resilient fallback WAV generator (24,000Hz mono 16-bit PCM WAV)
        wav_bytes = self._generate_fallback_wav(text, sample_rate=24000)
        gen_time = time.time() - t0
        return wav_bytes, gen_time, "fallback-pcm-synthesizer"

    def _generate_fallback_wav(self, text: str, sample_rate: int = 24000) -> bytes:
        """
        Generates standard 24kHz 16-bit PCM WAV audio representing spoken duration.
        Cadence is matched to text length (~150 words per minute / ~30ms per char).
        """
        duration = max(0.5, min(10.0, len(text) * 0.04))
        num_samples = int(duration * sample_rate)
        buf = io.BytesIO()

        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)

            # Generate pleasant soft acoustic tone modulated by speech rhythm
            samples = []
            words = text.split()
            word_count = max(1, len(words))

            for i in range(num_samples):
                t = i / sample_rate
                # Base speech frequency modulation
                base_freq = 220.0 + 30.0 * math.sin(2 * math.pi * 2.5 * t)
                # Formant envelope
                envelope = 0.5 * (1 + math.sin(2 * math.pi * (word_count / duration) * t))
                val = 0.15 * envelope * math.sin(2 * math.pi * base_freq * t)
                samples.append(int(32767 * val))

            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))

        return buf.getvalue()


tts_service = TTSService()
