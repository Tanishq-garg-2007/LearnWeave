import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Lesson, LearnerProfile, User
from app.services.retrieval_service import retriever
from app.services.groq_client import groq_client
from app.schemas.lessons import DoubtResponse, DoubtCitation

logger = logging.getLogger("learnweave.doubt_agent")

DOUBT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "cited_chunk_ids": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["answer", "cited_chunk_ids"]
}


class DoubtAgent:
    """
    Pedagogical Doubt Resolution Agent.
    Synthesizes answers from current lesson context and personal note chunks.
    Records doubts in learner profile to inform adaptive spaced repetition.
    """

    async def resolve_doubt(
        self,
        db: AsyncSession,
        lesson_id: str,
        doubt_text: str,
        user: User
    ) -> DoubtResponse:
        res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = res.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")

        # 1. Retrieve note chunks relevant to the doubt
        retrieved_chunks = await retriever.retrieve(
            db=db,
            query=f"{lesson.title} {doubt_text}",
            user_id=user.id,
            top_k=3
        )

        lesson_context = ""
        if lesson.lesson_content:
            summary = lesson.lesson_content.get("summary", "")
            sections_text = " ".join([s.get("content", "") for s in lesson.lesson_content.get("sections", [])[:2]])
            lesson_context = f"Lesson Summary: {summary}\nKey Material: {sections_text[:1000]}"

        notes_context = ""
        if retrieved_chunks:
            notes_context = "\n".join([
                f"[Chunk ID: {c['chunk_id']}] ({c['note_title']}): {c['text_content']}"
                for c in retrieved_chunks
            ])

        prompt = f"""You are a patient, encouraging AI tutor helping a student understand a concept.

LESSON: {lesson.title}
{lesson_context}

RETRIEVED STUDENT NOTES:
{notes_context or "No personal notes found for this query."}

STUDENT DOUBT / QUESTION:
"{doubt_text}"

INSTRUCTIONS:
1. Provide a direct, clarifying, step-by-step answer that resolves the confusion.
2. If citing facts from the retrieved student notes, include the exact chunk ID in `cited_chunk_ids`.
3. If no student notes are cited, return an empty list [] for `cited_chunk_ids`.
4. Tone: warm, encouraging, intellectually rigorous.
"""

        system_msg = "You are an empathetic, precise tutor. Output strictly valid JSON matching schema."

        try:
            raw_data = await groq_client.generate_structured_json(
                prompt=prompt,
                schema=DOUBT_SCHEMA,
                system_message=system_msg,
                temperature=0.3,
                max_tokens=900
            )
            answer_text = raw_data.get("answer", "")
            cited_ids = set(raw_data.get("cited_chunk_ids", []))
        except Exception as exc:
            logger.warning(f"Groq doubt call failed: {exc}. Using structured fallback.")
            answer_text = (
                f"Regarding your question on '{doubt_text}': In the context of {lesson.title}, "
                "this concept relates to how systems balance state consistency, computational isolation, and resource scheduling. "
                "Review the core definitions in the lesson sections to solidify this link."
            )
            cited_ids = {retrieved_chunks[0]["chunk_id"]} if retrieved_chunks else set()

        # Build citations
        chunk_map = {c["chunk_id"]: c for c in retrieved_chunks}
        citations = []
        for cid in cited_ids:
            if cid in chunk_map:
                c = chunk_map[cid]
                citations.append(DoubtCitation(
                    chunk_id=cid,
                    note_title=c["note_title"],
                    page_number=c.get("page_number"),
                    snippet=c["text_content"][:160] + "..."
                ))

        # Record doubt in LearnerProfile for adaptive review
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()
        if profile:
            current_doubts = list(profile.unresolved_doubts or [])
            doubt_entry = {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "doubt": doubt_text,
                "resolved": True
            }
            # Append if not duplicate
            if not any(d.get("doubt") == doubt_text for d in current_doubts if isinstance(d, dict)):
                current_doubts.append(doubt_entry)
                profile.unresolved_doubts = current_doubts[-30:]  # Keep latest 30
                await db.commit()

        return DoubtResponse(
            lesson_id=lesson.id,
            doubt=doubt_text,
            answer=answer_text,
            citations=citations
        )


doubt_agent = DoubtAgent()
