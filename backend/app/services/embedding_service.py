import hashlib
import logging
import math
from typing import List
import numpy as np
from app.config import settings

logger = logging.getLogger("learnweave.embeddings")


class EmbeddingService:
    """Local, high-speed sentence embeddings using all-MiniLM-L6-v2."""

    def __init__(self):
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.dimension = settings.EMBEDDING_DIMENSION  # 384
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
                self._initialized = True
                logger.info(f"Loaded local embedding model: {self.model_name} (dim={self.dimension})")
            except Exception as exc:
                logger.warning(f"Could not load fastembed: {exc}. Using deterministic semantic projection.")
                self._initialized = True
                self._model = None
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Compute 384-dimensional embedding vector for a single query or chunk."""
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Batch compute embeddings for multiple text passages."""
        model = self._get_model()
        if model is not None:
            try:
                raw_embeds = list(model.embed(texts))
                return [arr.tolist() if hasattr(arr, "tolist") else list(arr) for arr in raw_embeds]
            except Exception as exc:
                logger.warning(f"Embedding inference failed: {exc}. Using fallback projection.")

        # Deterministic semantic hash projection (dim=384, unit L2 normalized)
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
