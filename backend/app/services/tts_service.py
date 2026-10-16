import io
import logging
import math
import struct
import time
import wave
from pathlib import Path
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger("learnweave.tts")


class TTSService:
    """Centralized Text-to-Speech service with Kokoro-82M support and valid WAV fallback."""
    def __init__(self):
        self.model_path = Path(settings.KOKORO_MODEL_PATH)
        self.voices_path = Path(settings.KOKORO_VOICES_PATH)
        self._kokoro = None
        self._initialized = False

    def initialize_kokoro(self) -> Tuple[bool, float]:
        """Attempt to load Kokoro-82M ONNX model. Returns (success, load_time_seconds)."""
        t0 = time.time()
        try:
            if not self.model_path.exists():
                logger.info(f"Kokoro weights not found at {self.model_path}. Using standard WAV synthesizer.")
                return False, time.time() - t0

            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro(str(self.model_path), str(self.voices_path))
            self._initialized = True
            load_time = time.time() - t0
            logger.info(f"Kokoro-82M loaded in {load_time:.3f}s")
            return True, load_time
        except Exception as exc:
            logger.warning(f"Kokoro-82M initialization skipped/failed: {exc}. Falling back to standard audio generator.")
            return False, time.time() - t0

    def synthesize_wav(self, text: str, voice: str = "af_heart", speed: float = 1.0) -> Tuple[bytes, float, str]:
        """
        Synthesize text to WAV audio bytes.
        Returns: (wav_bytes, generation_time_seconds, engine_used)
        """
        t0 = time.time()

        if self._initialized and self._kokoro is not None:
            try:
                samples, sample_rate = self._kokoro.create(text, voice=voice, speed=speed, lang="en-us")
                import soundfile as sf
                buf = io.BytesIO()
                sf.write(buf, samples, sample_rate, format="WAV")
                gen_time = time.time() - t0
                return buf.getvalue(), gen_time, "kokoro-82m"
            except Exception as exc:
                logger.warning(f"Kokoro synthesis failed: {exc}. Using fallback WAV engine.")

        # Resilient fallback WAV generator (24,000Hz mono 16-bit PCM WAV)
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
