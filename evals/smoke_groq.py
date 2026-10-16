import asyncio
import io
import math
import struct
import sys
import time
import wave
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings
from app.services.groq_client import GroqClient, GroqClientError
from pydantic import BaseModel


class TestStructuredResponse(BaseModel):
    message: str
    confidence: float
    model_name: str


async def run_groq_smoke_tests():
    print("=" * 60)
    print("LEARNWEAVE AI — GROQ SMOKE TEST RUNNER")
    print("=" * 60)

    client = GroqClient()
    results = {}

    # Test 1: Primary Model (qwen/qwen3.8-27b)
    print(f"\n[1/4] Testing Primary Model: {client.primary_model}...")
    t0 = time.time()
    try:
        resp = await client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a concise AI tutor."},
                {"role": "user", "content": "State the single core goal of LearnWeave AI in 10 words or less."}
            ],
            model=client.primary_model,
            max_tokens=60
        )
        latency = time.time() - t0
        content = resp["choices"][0]["message"]["content"].strip()
        usage = resp.get("usage", {})
        print(f"  ✓ SUCCESS in {latency:.3f}s")
        print(f"  Response: \"{content}\"")
        print(f"  Prompt tokens: {usage.get('prompt_tokens')} | Completion tokens: {usage.get('completion_tokens')}")
        results["primary_model"] = {"status": "PASS", "latency": latency, "tokens": usage.get("total_tokens", 0)}
    except Exception as exc:
        print(f"  ✗ FAILED: {exc}")
        results["primary_model"] = {"status": "FAIL", "error": str(exc)}

    # Test 2: Structured JSON Output on Primary Model
    print(f"\n[2/4] Testing Structured Output Validation on {client.primary_model}...")
    t0 = time.time()
    try:
        structured_res = await client.structured_completion(
            messages=[
                {"role": "system", "content": "You are a curriculum validator."},
                {"role": "user", "content": "Respond with message='Roadmap validated', confidence=0.98, model_name='qwen3.8-27b'"}
            ],
            schema=TestStructuredResponse,
            model=client.primary_model,
            max_tokens=100
        )
        latency = time.time() - t0
        print(f"  ✓ SUCCESS in {latency:.3f}s")
        print(f"  Validated Object: {structured_res.model_dump()}")
        results["structured_output"] = {"status": "PASS", "latency": latency}
    except Exception as exc:
        print(f"  ✗ FAILED: {exc}")
        results["structured_output"] = {"status": "FAIL", "error": str(exc)}

    # Test 3: Fallback Model (openai/gpt-oss-20b)
    print(f"\n[3/4] Testing Fallback Model: {client.fallback_model}...")
    t0 = time.time()
    try:
        resp_fb = await client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'LearnWeave fallback active'"}
            ],
            model=client.fallback_model,
            max_tokens=60
        )
        latency = time.time() - t0
        fb_content = resp_fb["choices"][0]["message"]["content"].strip()
        usage_fb = resp_fb.get("usage", {})
        print(f"  ✓ SUCCESS in {latency:.3f}s")
        print(f"  Response: \"{fb_content}\"")
        results["fallback_model"] = {"status": "PASS", "latency": latency, "tokens": usage_fb.get("total_tokens", 0)}
    except Exception as exc:
        print(f"  ✗ FAILED: {exc}")
        results["fallback_model"] = {"status": "FAIL", "error": str(exc)}

    # Test 4: Whisper Speech-to-Text (whisper-large-v3-turbo)
    print(f"\n[4/4] Testing Whisper Speech-to-Text: {client.stt_model}...")
    t0 = time.time()
    try:
        # Generate 1-second 440Hz test audio WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            samples = [int(32767 * 0.1 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(16000)]
            w.writeframes(struct.pack("<" + "h" * len(samples), *samples))
        audio_bytes = buf.getvalue()

        transcript = await client.transcribe_audio(audio_bytes, filename="smoke_test.wav")
        latency = time.time() - t0
        print(f"  ✓ SUCCESS in {latency:.3f}s")
        print(f"  Transcript: \"{transcript}\" (Audio was pure tone, transcript response returned without error)")
        results["whisper_stt"] = {"status": "PASS", "latency": latency, "transcript_length": len(transcript)}
    except Exception as exc:
        print(f"  ✗ FAILED: {exc}")
        results["whisper_stt"] = {"status": "FAIL", "error": str(exc)}

    print("\n" + "=" * 60)
    print("GROQ SMOKE TEST SUMMARY")
    print("=" * 60)
    all_passed = all(r.get("status") == "PASS" for r in results.values())
    for k, v in results.items():
        print(f"  {k:20s}: {v.get('status')} (latency: {v.get('latency', 0):.3f}s)")
    print("=" * 60)
    if all_passed:
        print("ALL GROQ SMOKE CHECKS PASSED!\n")
    else:
        print("SOME GROQ SMOKE CHECKS FAILED!\n")
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_groq_smoke_tests())
    sys.exit(0 if success else 1)
