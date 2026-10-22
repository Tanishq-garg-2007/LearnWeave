import hashlib
import logging
import math
import threading
from typing import List, Optional
import httpx
import numpy as np
from app.config import settings

logger = logging.getLogger("learnweave.embeddings")


class EmbeddingService:
    """Hybrid sentence embedding service: Google AI Studio hosted (384-d) with FastEmbed & local fallback."""

    def __init__(self):
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.dimension = settings.EMBEDDING_DIMENSION  # 384
        self._model = None
        self._initialized = False
        # Uploads embed in worker threads, so the one-time model load must not run twice.
        self._load_lock = threading.Lock()

    def _get_model(self):
        # Double-checked locking: once the load has finished, callers take no lock.
        if self._initialized:
            return self._model
        with self._load_lock:
            if not self._initialized:
                try:
                    from fastembed import TextEmbedding
                    self._model = TextEmbedding(model_name=self.model_name)
                    logger.info(f"Loaded local embedding model: {self.model_name} (dim={self.dimension})")
                except Exception as exc:
                    logger.warning(f"Could not load fastembed: {exc}. Using deterministic semantic projection.")
                    self._model = None
                self._initialized = True
        return self._model

    def warm_up(self) -> bool:
        """Load the model if it is not loaded yet."""
        if settings.GEMINI_API_KEY:
            return True
        return self._get_model() is not None

    def embed_text(self, text: str) -> List[float]:
        """Compute 384-dimensional embedding vector for a single query or chunk."""
        return self.embed_documents([text])[0]

    def _embed_with_gemini(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Fetch 384-d Matryoshka embeddings from Google AI Studio / Gemini API."""
        if not settings.GEMINI_API_KEY:
            return None

        model = settings.GEMINI_EMBEDDING_MODEL.strip()
        if not model.startswith("models/"):
            model = f"models/{model}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents?key={settings.GEMINI_API_KEY}"

        # Google Gemini batchEmbedContents accepts up to 100 texts per batch
        batch_size = 100
        all_embeddings: List[List[float]] = []

        try:
            with httpx.Client(timeout=30.0) as client:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    requests = [
                        {
                            "model": model,
                            "content": {"parts": [{"text": t}]},
                            "outputDimensionality": self.dimension,
                        }
                        for t in batch
                    ]
                    resp = client.post(url, json={"requests": requests})
                    if resp.status_code != 200:
                        logger.warning(f"Gemini embedding API returned status {resp.status_code}: {resp.text[:200]}")
                        return None
                    data = resp.json()
                    embeds = data.get("embeddings", [])
                    for e in embeds:
                        vals = e.get("values", [])
                        if len(vals) == self.dimension:
                            all_embeddings.append(vals)
                        else:
                            logger.warning(f"Unexpected Gemini embedding length {len(vals)}, expected {self.dimension}")
                            return None
            return all_embeddings
        except Exception as exc:
            logger.warning(f"Gemini embedding request failed: {exc}. Falling back to local engine.")
            return None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch compute embeddings for multiple text passages."""
        # 1. Try Google AI Studio hosted embeddings first if configured
        if settings.GEMINI_API_KEY:
            gemini_embeds = self._embed_with_gemini(texts)
            if gemini_embeds is not None and len(gemini_embeds) == len(texts):
                return gemini_embeds

        # 2. Try local FastEmbed model
        model = self._get_model()
        if model is not None:
            try:
                raw_embeds = list(model.embed(texts))
                return [arr.tolist() if hasattr(arr, "tolist") else list(arr) for arr in raw_embeds]
            except Exception as exc:
                logger.warning(f"Local embedding inference failed: {exc}. Using fallback projection.")

        # 3. Deterministic semantic hash projection (dim=384, unit L2 normalized)
        vectors = []
        for text in texts:
            words = text.lower().split()
            vec = np.zeros(self.dimension, dtype=np.float32)
            if not words:
                vec[0] = 1.0
                vectors.append(vec.tolist())
                continue

            for word in words:
                h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                idx = h % self.dimension
                sign = 1.0 if ((h >> 8) & 1) else -1.0
                vec[idx] += sign

            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            else:
                vec[0] = 1.0
            vectors.append(vec.tolist())
        return vectors


embedding_service = EmbeddingService()
