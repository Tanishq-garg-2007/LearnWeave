import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError
from app.config import settings

logger = logging.getLogger("learnweave.groq")
T = TypeVar("T", bound=BaseModel)


class GroqClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class GroqUsageTracker:
    """Thread-safe rolling-minute and daily token/request budget tracker."""
    def __init__(self):
        self._lock = asyncio.Lock()
        self.minute_requests: List[float] = []
        self.minute_tokens: List[tuple[float, int]] = []
        self.daily_tokens = 0
        self.daily_requests = 0
        self.last_day_reset = time.time()

    async def check_and_reserve(self, estimated_tokens: int, max_rpm: int = 28, max_tpm: int = 8000):
        while True:
            sleep_needed = 0.0
            async with self._lock:
                now = time.time()
                if now - self.last_day_reset > 86400:
                    self.daily_tokens = 0
                    self.daily_requests = 0
                    self.last_day_reset = now

                self.minute_requests = [t for t in self.minute_requests if now - t < 60]
                self.minute_tokens = [(t, tok) for t, tok in self.minute_tokens if now - t < 60]

                curr_tokens = sum(tok for _, tok in self.minute_tokens)
                if len(self.minute_requests) >= max_rpm and self.minute_requests:
                    sleep_needed = max(0.2, min(5.0, 60 - (now - self.minute_requests[0]) + 0.1))
                elif curr_tokens > 0 and (curr_tokens + estimated_tokens) > max_tpm and self.minute_tokens:
                    sleep_needed = max(0.2, min(5.0, 60 - (now - self.minute_tokens[0][0]) + 0.1))
                else:
                    self.minute_requests.append(time.time())
                    self.minute_tokens.append((time.time(), min(estimated_tokens, 1200)))
                    self.daily_requests += 1
                    self.daily_tokens += min(estimated_tokens, 1200)
                    return

            if sleep_needed > 0:
                logger.info(f"Groq rate guard pacing request for {sleep_needed:.2f}s")
                await asyncio.sleep(sleep_needed)


class GroqClient:
    """Centralized resilient client for Groq Cloud API."""
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.base_url = "https://api.groq.com/openai/v1"
        self.primary_model = settings.GROQ_PRIMARY_MODEL
        self.fallback_model = settings.GROQ_FALLBACK_MODEL
        self.stt_model = settings.GROQ_STT_MODEL
        self.reasoning_mode = settings.GROQ_REASONING_MODE
        self.timeout = settings.GROQ_TIMEOUT_SECONDS
        self.max_retries = settings.GROQ_MAX_RETRIES
        self.max_combined_tokens = settings.GROQ_MAX_COMBINED_TOKENS
        self.tracker = GroqUsageTracker()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LearnWeave-AI/1.0"
        }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 900,
        temperature: float = 0.3,
        response_format: Optional[Dict[str, Any]] = None,
        enable_fallback: bool = True
    ) -> Dict[str, Any]:
        """Execute chat completion with rate-limiting, retries, and fallback."""
        selected_model = model or self.primary_model
        estimated_input_tokens = sum(len(m.get("content", "").split()) * 2 for m in messages)
        total_estimated = estimated_input_tokens + min(max_tokens, 900)

        if total_estimated > self.max_combined_tokens:
            raise GroqClientError(
                f"Combined estimated tokens ({total_estimated}) exceeds configured limit ({self.max_combined_tokens})",
                retryable=False
            )

        models_to_try = [selected_model]
        if enable_fallback and selected_model != self.fallback_model:
            models_to_try.append(self.fallback_model)

        last_error = None
        for current_model in models_to_try:
            actual_max_tokens = min(max_tokens, 900) if "qwen" in current_model.lower() else max_tokens
            max_retries = 5  # Allow sufficient window for rolling 60s Groq limit resets

            for attempt in range(max_retries):
                try:
                    await self.tracker.check_and_reserve(total_estimated)
                    payload: Dict[str, Any] = {
                        "model": current_model,
                        "messages": messages,
                        "max_tokens": actual_max_tokens,
                        "temperature": temperature,
                    }
                    if self.reasoning_mode and "qwen" in current_model.lower():
                        payload["reasoning_format"] = self.reasoning_mode
                    if response_format:
                        payload["response_format"] = response_format

                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        resp = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers=self._get_headers(),
                            json=payload
                        )

                        if resp.status_code == 200:
                            data = resp.json()
                            usage = data.get("usage", {})
                            logger.info(
                                f"Groq success | model={current_model} | "
                                f"tokens={usage.get('total_tokens', 0)} | latency={usage.get('total_time', 0):.3f}s"
                            )
                            return data

                        if resp.status_code in (429, 500, 502, 503, 504):
                            try:
                                retry_after = float(resp.headers.get("retry-after", "3"))
                            except ValueError:
                                retry_after = 3.0
                            raw_backoff = max(retry_after, (5.0 * (attempt + 1)) + random.uniform(0.5, 2.0))
                            backoff = min(40.0, max(2.0, raw_backoff))
                            logger.warning(
                                f"Groq HTTP {resp.status_code} on {current_model}. Attempt {attempt + 1}/{max_retries}. Backoff {backoff:.2f}s (retry-after={retry_after}s)"
                            )
                            await asyncio.sleep(backoff)
                            continue

                        # Handle json_validate_failed by retrying without json_object mode
                        error_body = resp.text
                        if resp.status_code == 400 and "json_validate_failed" in error_body and response_format:
                            logger.warning(f"Groq json_validate_failed on {current_model}. Retrying without response_format constraint.")
                            payload.pop("response_format", None)
                            retry_resp = await client.post(
                                f"{self.base_url}/chat/completions",
                                headers=self._get_headers(),
                                json=payload
                            )
                            if retry_resp.status_code == 200:
                                return retry_resp.json()

                        # Client error (400, 401, 403, 404)
                        logger.error(f"Groq permanent error {resp.status_code}: {error_body}")
                        raise GroqClientError(f"Groq API error {resp.status_code}: {error_body}", status_code=resp.status_code)

                except httpx.RequestError as exc:
                    logger.warning(f"Groq network error on {current_model}: {exc}. Attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(min(6.0, (2 ** attempt) + random.uniform(0.1, 0.5)))
                    last_error = exc

            logger.warning(f"Model {current_model} exhausted retries. Attempting next candidate if available.")

        raise GroqClientError(f"All Groq models failed. Last error: {last_error}", retryable=False)

    def _extract_json_str(self, text: str) -> str:
        """Extract clean JSON substring from text or markdown code fences."""
        cleaned = text.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                p = part.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                start = p.find("{")
                end = p.rfind("}")
                if start != -1 and end != -1:
                    return p[start:end + 1]
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            return cleaned[start:end + 1]
        return cleaned

    async def structured_completion(
        self,
        messages: List[Dict[str, str]],
        schema: Type[T],
        model: Optional[str] = None,
        max_tokens: int = 900,
        temperature: float = 0.2
    ) -> T:
        """Execute chat completion and parse into Pydantic schema with 1 bounded repair retry."""
        system_instruction = (
            f"\nYou must return ONLY a valid JSON object matching this schema:\n"
            f"{json.dumps(schema.model_json_schema())}\nDo not include backticks or markdown."
        )
        augmented_messages = list(messages)
        augmented_messages[0] = {
            "role": augmented_messages[0]["role"],
            "content": augmented_messages[0]["content"] + system_instruction
        }

        raw_response = await self.chat_completion(
            messages=augmented_messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        content = raw_response["choices"][0]["message"]["content"]
        json_str = self._extract_json_str(content)
        try:
            return schema.model_validate_json(json_str)
        except ValidationError as err:
            logger.warning(f"Schema validation failed on first attempt: {err}. Triggering repair retry.")
            repair_messages = list(augmented_messages) + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Your JSON response failed validation: {err}. Please fix and return ONLY valid JSON matching the schema."}
            ]
            repair_resp = await self.chat_completion(
                messages=repair_messages,
                model=model,
                max_tokens=max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            repair_content = repair_resp["choices"][0]["message"]["content"]
            repair_json = self._extract_json_str(repair_content)
            try:
                return schema.model_validate_json(repair_json)
            except ValidationError as final_err:
                logger.error(f"Structured completion repair failed: {final_err}")
                raise GroqClientError(f"Failed to produce schema-valid output: {final_err}")

    async def generate_structured_json(
        self,
        prompt: str,
        schema: Optional[Dict[str, Any]] = None,
        system_message: str = "You are an expert AI tutor. Output strictly valid JSON.",
        temperature: float = 0.2,
        max_tokens: int = 900,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convenience method to generate JSON directly matching an optional JSON Schema."""
        schema_instruction = ""
        if schema:
            schema_instruction = f"\nReturn strictly valid JSON matching this schema:\n{json.dumps(schema)}\nDo not include markdown blocks."
        messages = [
            {"role": "system", "content": system_message + schema_instruction},
            {"role": "user", "content": prompt}
        ]
        resp = await self.chat_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        content = resp["choices"][0]["message"]["content"]
        json_clean = self._extract_json_str(content)
        try:
            return json.loads(json_clean)
        except json.JSONDecodeError as err:
            logger.warning(f"JSON parsing error: {err}. Attempting clean slice.")
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return json.loads(content[start:end + 1])
            raise GroqClientError(f"Failed to parse JSON response: {err}")

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcribe speech using Groq whisper-large-v3-turbo."""
        if not audio_bytes:
            raise GroqClientError("Empty audio content provided", retryable=False)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "LearnWeave-AI/1.0"
        }
        files = {
            "file": (filename, audio_bytes, "audio/wav"),
            "model": (None, self.stt_model)
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(
                        f"{self.base_url}/audio/transcriptions",
                        headers=headers,
                        files=files
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data.get("text", "").strip()

                    if resp.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(min(6.0, (2 ** attempt) + 1.0))
                        continue

                    raise GroqClientError(f"STT error {resp.status_code}: {resp.text}", status_code=resp.status_code)
            except httpx.RequestError as exc:
                if attempt == self.max_retries - 1:
                    raise GroqClientError(f"STT network error: {exc}", retryable=True)
                await asyncio.sleep(2 ** attempt)

        raise GroqClientError("STT retries exhausted", retryable=True)


groq_client = GroqClient()
