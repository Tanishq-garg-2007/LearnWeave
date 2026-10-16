import io
import sys
import time
import wave
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.tts_service import tts_service


def run_kokoro_smoke_tests():
    print("=" * 60)
    print("LEARNWEAVE AI — KOKORO & TTS SMOKE TEST RUNNER")
    print("=" * 60)

    # Step 1: Model Initialization Check
    print("\n[1/3] Initializing Kokoro-82M TTS Engine...")
    kokoro_loaded, load_time = tts_service.initialize_kokoro()
    if kokoro_loaded:
        print(f"  ✓ Kokoro-82M ONNX model loaded successfully in {load_time:.3f}s")
    else:
        print(f"  ℹ Kokoro-82M ONNX weights not detected locally (tested in {load_time:.3f}s). Using resilient 24kHz PCM WAV synthesis engine.")

    # Step 2: Synthesis Check
    sample_text = "Welcome to LearnWeave AI, your personal adaptive learning companion."
    print(f"\n[2/3] Synthesizing speech for test phrase:\n  \"{sample_text}\"")

    t0 = time.time()
    wav_bytes, gen_time, engine = tts_service.synthesize_wav(sample_text)
    total_time = time.time() - t0

    print(f"  ✓ Synthesis complete using engine: '{engine}'")
    print(f"  ✓ Generation time: {gen_time:.3f}s (Total pipeline: {total_time:.3f}s)")
    print(f"  ✓ Output size: {len(wav_bytes):,} bytes")

    # Step 3: Validate WAV Headers & Format
    print("\n[3/3] Validating WAV headers and format...")
    try:
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as w:
            channels = w.getnchannels()
            width = w.getsampwidth()
            framerate = w.getframerate()
            nframes = w.getnframes()
            duration = nframes / float(framerate)

        print(f"  ✓ Channels: {channels} (Expected: 1 mono)")
        print(f"  ✓ Sample Width: {width * 8}-bit (Expected: 16-bit)")
        print(f"  ✓ Sample Rate: {framerate} Hz")
        print(f"  ✓ Duration: {duration:.2f} seconds")
        print(f"  ✓ Frame Count: {nframes:,} frames")

        assert channels == 1, "Channels must be mono"
        assert width == 2, "Sample width must be 16-bit"
        assert framerate in (24000, 22050, 16000), "Standard sample rate required"
        assert duration > 0.5, "Duration must be valid non-empty audio"
        print("  ✓ WAV Validation: PASSED")

    except Exception as exc:
        print(f"  ✗ WAV Validation FAILED: {exc}")
        return False

    # Save output for inspection
    out_dir = Path(__file__).resolve().parent / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_wav = out_dir / "smoke_tts_sample.wav"
    out_wav.write_bytes(wav_bytes)
    print(f"\n  Saved smoke audio to: {out_wav}")

    print("\n" + "=" * 60)
    print("TTS SMOKE TEST SUMMARY: PASSED")
    print(f"Engine: {engine} | Gen Time: {gen_time:.3f}s | Duration: {duration:.2f}s")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    success = run_kokoro_smoke_tests()
    sys.exit(0 if success else 1)
