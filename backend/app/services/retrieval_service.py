import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.api.sql_utils import escape_like
from app.db.models import NoteChunk, Note
from app.services.embedding_service import embedding_service

logger = logging.getLogger("learnweave.retrieval")


@dataclass
class RetrievalResult:
    """Outcome of one hybrid retrieval.

    ``degraded`` is True when at least one search leg failed. Callers must treat
    the result as incomplete: it is not an authoritative "no notes exist" answer.
    """
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    degraded: bool = False
    errors: List[str] = field(default_factory=list)


class HybridRetriever:
    """
    Hybrid RAG Retriever combining pgvector cosine distance search
    and PostgreSQL full-text search fused via Reciprocal Rank Fusion (RRF, k=60).
    Enforces strict user isolation at the database level.

    Every database search runs inside a SAVEPOINT, so a failing statement is rolled
    back on its own and the caller's transaction stays usable. Failures are logged
    and reported through ``RetrievalResult.degraded`` rather than swallowed.
    """

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        user_id: str,
        top_k: int = 4,
        candidate_limit: int = 15,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convenience wrapper returning only the fused chunks (see retrieve_detailed)."""
        result = await self.retrieve_detailed(
            db=db,
            query=query,
            user_id=user_id,
            top_k=top_k,
            candidate_limit=candidate_limit,
            subject=subject,
        )
        return result.chunks

    async def retrieve_detailed(
        self,
        db: AsyncSession,
        query: str,
        user_id: str,
        top_k: int = 4,
        candidate_limit: int = 15,
        subject: Optional[str] = None
    ) -> RetrievalResult:
        """
        Execute hybrid retrieval for a given user query.
        Returns top_k chunks fused by RRF score, plus a degraded flag if any leg failed.
        """
        if not query or not query.strip():
            return RetrievalResult()

        clean_query = query.strip()
        errors: List[str] = []
        vector_candidates: List[Dict[str, Any]] = []
        sparse_candidates: List[Dict[str, Any]] = []

        # 1. Dense Vector Search
        try:
            # ONNX inference is CPU-bound; keep it off the event loop.
            query_vector = await asyncio.to_thread(embedding_service.embed_text, clean_query)
            vector_candidates = await self._dense_search(
                db=db,
                query_vector=query_vector,
                user_id=user_id,
                limit=candidate_limit,
                subject=subject
            )
        except Exception as exc:
            logger.error(f"Dense retrieval leg failed for user {user_id}: {exc!r}", exc_info=True)
            errors.append(f"dense: {type(exc).__name__}")

        # 2. Sparse Full-Text Search
        try:
            sparse_candidates = await self._sparse_search(
                db=db,
                query_text=clean_query,
                user_id=user_id,
                limit=candidate_limit,
                subject=subject
            )
        except Exception as exc:
            logger.error(f"Sparse retrieval leg failed for user {user_id}: {exc!r}", exc_info=True)
            errors.append(f"sparse: {type(exc).__name__}")

        # 3. Reciprocal Rank Fusion (k=60)
        fused = self._reciprocal_rank_fusion(
            vector_results=vector_candidates,
            sparse_results=sparse_candidates,
            k=self.rrf_k
        )

        degraded = bool(errors)
        if degraded:
            logger.warning(f"Retrieval degraded for user {user_id}: {errors}")
        return RetrievalResult(chunks=fused[:top_k], degraded=degraded, errors=errors)

    async def _dense_search(
        self,
        db: AsyncSession,
        query_vector: List[float],
        user_id: str,
        limit: int,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Dense similarity search using pgvector cosine distance. Raises on failure."""
        distance_col = NoteChunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = (
            select(
                NoteChunk.id,
                NoteChunk.note_id,
                NoteChunk.owner_id,
                NoteChunk.chunk_index,
                NoteChunk.text_content,
                NoteChunk.page_number,
                Note.title.label("note_title"),
                Note.subject.label("note_subject"),
                distance_col
            )
            .join(Note, NoteChunk.note_id == Note.id)
            .where(NoteChunk.owner_id == user_id)
        )

        if subject:
            stmt = stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))

        stmt = stmt.order_by(distance_col.asc()).limit(limit)
        async with self._savepoint(db):
            result = await db.execute(stmt)
            rows = result.all()

        return [
            {
                "chunk_id": row.id,
                "note_id": row.note_id,
                "owner_id": row.owner_id,
                "chunk_index": row.chunk_index,
                "text_content": row.text_content,
                "page_number": row.page_number,
                "note_title": row.note_title,
                "note_subject": row.note_subject,
                "distance": float(row.distance) if row.distance is not None else 1.0,
                "source": "vector"
            }
            for row in rows
        ]

    async def _sparse_search(
        self,
        db: AsyncSession,
        query_text: str,
        user_id: str,
        limit: int,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Sparse search using PostgreSQL full-text search. Falls back to ILIKE if FTS fails."""
        try:
            # ts_rank calculation
            rank_col = func.ts_rank_cd(
                func.to_tsvector("english", NoteChunk.text_content),
                func.plainto_tsquery("english", query_text)
            ).label("rank")

            stmt = (
                select(
                    NoteChunk.id,
                    NoteChunk.note_id,
                    NoteChunk.owner_id,
                    NoteChunk.chunk_index,
                    NoteChunk.text_content,
                    NoteChunk.page_number,
                    Note.title.label("note_title"),
                    Note.subject.label("note_subject"),
                    rank_col
                )
                .join(Note, NoteChunk.note_id == Note.id)
                .where(
                    and_(
                        NoteChunk.owner_id == user_id,
                        func.to_tsvector("english", NoteChunk.text_content).op("@@")(
                            func.plainto_tsquery("english", query_text)
                        )
                    )
                )
            )

            if subject:
                stmt = stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))

            stmt = stmt.order_by(rank_col.desc()).limit(limit)
            async with self._savepoint(db):
                result = await db.execute(stmt)
                rows = result.all()

            return [
                {
                    "chunk_id": row.id,
                    "note_id": row.note_id,
                    "owner_id": row.owner_id,
                    "chunk_index": row.chunk_index,
                    "text_content": row.text_content,
                    "page_number": row.page_number,
                    "note_title": row.note_title,
                    "note_subject": row.note_subject,
                    "rank": float(row.rank) if row.rank is not None else 0.0,
                    "source": "fts"
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning(f"Sparse FTS search encountered issue: {exc!r}. Trying fallback ilike search.")
            return await self._sparse_ilike_fallback(db, query_text, user_id, limit, subject)

    async def _sparse_ilike_fallback(
        self,
        db: AsyncSession,
        query_text: str,
        user_id: str,
        limit: int,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback substring search if FTS query parsing encounters edge case. Raises on failure."""
        tokens = [t for t in query_text.split() if len(t) > 3][:3]
        if not tokens:
            return []

        conditions = [NoteChunk.text_content.ilike(f"%{escape_like(tok)}%", escape="\\") for tok in tokens]
        stmt = (
            select(
                NoteChunk.id,
                NoteChunk.note_id,
                NoteChunk.owner_id,
                NoteChunk.chunk_index,
                NoteChunk.text_content,
                NoteChunk.page_number,
                Note.title.label("note_title"),
                Note.subject.label("note_subject")
            )
            .join(Note, NoteChunk.note_id == Note.id)
            .where(and_(NoteChunk.owner_id == user_id, *conditions))
            .limit(limit)
        )
        if subject:
            stmt = stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))

        async with self._savepoint(db):
            res = await db.execute(stmt)
            rows = res.all()

        return [{
            "chunk_id": r.id,
            "note_id": r.note_id,
            "owner_id": r.owner_id,
            "chunk_index": r.chunk_index,
            "text_content": r.text_content,
            "page_number": r.page_number,
            "note_title": r.note_title,
            "note_subject": r.note_subject,
            "rank": 0.1,
            "source": "ilike"
        } for r in rows]

    @staticmethod
    def _savepoint(db: AsyncSession):
        """SAVEPOINT scope: a failing statement rolls back only itself, not the caller's transaction."""
        return db.begin_nested()

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Merge ranked lists from dense vector search and sparse FTS
        using Reciprocal Rank Fusion: score = sum(1 / (k + rank)).
        """
        doc_scores: Dict[str, float] = {}
        doc_data: Dict[str, Dict[str, Any]] = {}
        sources: Dict[str, List[str]] = {}

        # Add vector rankings (rank starts at 1)
        for rank, doc in enumerate(vector_results, start=1):
            cid = doc["chunk_id"]
            rrf_score = 1.0 / (k + rank)
            doc_scores[cid] = doc_scores.get(cid, 0.0) + rrf_score
            doc_data[cid] = doc
            sources.setdefault(cid, []).append("vector")

        # Add sparse rankings (rank starts at 1)
        for rank, doc in enumerate(sparse_results, start=1):
            cid = doc["chunk_id"]
            rrf_score = 1.0 / (k + rank)
            doc_scores[cid] = doc_scores.get(cid, 0.0) + rrf_score
            if cid not in doc_data:
                doc_data[cid] = doc
            sources.setdefault(cid, []).append("fts")

        # Compile and sort by RRF score descending
        fused = []
        for cid, score in doc_scores.items():
            entry = dict(doc_data[cid])
            entry["rrf_score"] = round(score, 6)
            entry["sources"] = sources.get(cid, [])
            fused.append(entry)

        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused


retriever = HybridRetriever(rrf_k=60)
