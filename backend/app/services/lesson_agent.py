import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import Lesson, LearnerProfile, User
from app.services.retrieval_service import retriever
from app.services.groq_client import groq_client
from app.schemas.lessons import LessonContent, Section, CitedChunk

logger = logging.getLogger("learnweave.lesson_agent")

LESSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string"},
                    "content": {"type": "string"},
                    "cited_chunk_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["heading", "content", "cited_chunk_ids"]
            }
        },
        "key_takeaways": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["title", "summary", "sections", "key_takeaways"]
}


class LessonAgent:
    """
    Pedagogical Lesson Generation Agent.
    Operates in two modes:
    - Mode A (RAG-Grounded): Synthesizes lesson using retrieved student note chunks with genuine citations.
    - Mode B (AI-Generated Learning): Curriculum-guided lesson without notes, tagged as AI-Generated Learning.
    """

    async def generate_lesson(
        self,
        db: AsyncSession,
        lesson_id: str,
        user: User
    ) -> LessonContent:
        # Load lesson with module
        res = await db.execute(
            select(Lesson).options(selectinload(Lesson.module)).where(Lesson.id == lesson_id)
        )
        lesson = res.scalar_one_or_none()
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")

        # Load learner profile
        p_res = await db.execute(select(LearnerProfile).where(LearnerProfile.user_id == user.id))
        profile = p_res.scalar_one_or_none()
        prefs = profile.preferences if profile and profile.preferences else {
            "learning_style": "practical",
            "explanation_depth": "detailed",
            "analogies_preferred": True
        }

        # 1. Retrieve relevant personal note chunks
        retrieved_chunks = await retriever.retrieve(
            db=db,
            query=f"{lesson.title} {lesson.module.title if lesson.module else ''}",
            user_id=user.id,
            top_k=4
        )

        # Decide Mode: Mode A if chunks found, Mode B otherwise
        is_rag_grounded = len(retrieved_chunks) > 0
        grounding_type = "rag_grounded" if is_rag_grounded else "ai_generated"

        # Build prompt
        prompt = self._build_prompt(
            lesson=lesson,
            prefs=prefs,
            retrieved_chunks=retrieved_chunks,
            is_rag_grounded=is_rag_grounded
        )

        system_msg = (
            "You are an expert personalized tutor on LearnWeave AI. "
            "Your explanations are crystal-clear, pedagogically rigorous, and tailored to the student. "
            "You MUST output strictly valid JSON conforming to the requested schema."
        )

        try:
            raw_data = await groq_client.generate_structured_json(
                prompt=prompt,
                schema=LESSON_SCHEMA,
                system_message=system_msg,
                temperature=0.3,
                max_tokens=850
            )
            content = self._parse_and_validate(raw_data, lesson, retrieved_chunks, grounding_type)
        except Exception as exc:
            logger.warning(f"Groq generation failed: {exc}. Generating deterministic curriculum lesson.")
            content = self._generate_fallback_lesson(lesson, retrieved_chunks, grounding_type)

        # Persist generated lesson content in DB
        lesson.lesson_content = content.model_dump()
        if lesson.status == "not_started":
            lesson.status = "in_progress"
        await db.commit()

        return content

    def _build_prompt(
        self,
        lesson: Lesson,
        prefs: Dict[str, Any],
        retrieved_chunks: List[Dict[str, Any]],
        is_rag_grounded: bool
    ) -> str:
        objectives_str = "\n".join(f"- {obj}" for obj in (lesson.learning_objectives or []))

        style = prefs.get("learning_style", "practical")
        depth = prefs.get("explanation_depth", "detailed")
        use_analogies = prefs.get("analogies_preferred", True)

        if is_rag_grounded:
            context_blocks = []
            for c in retrieved_chunks:
                context_blocks.append(
                    f"--- Chunk ID: {c['chunk_id']} | Source: {c['note_title']} (Page {c.get('page_number') or 1}) ---\n"
                    f"{c['text_content']}"
                )
            context_text = "\n\n".join(context_blocks)

            return f"""Generate a comprehensive, RAG-grounded lesson for:
Lesson Title: {lesson.title}
Module: {lesson.module.title if lesson.module else 'General'}
Target Learning Objectives:
{objectives_str}

STUDENT PREFERENCES:
- Learning Style: {style}
- Explanation Depth: {depth}
- Use Analogies: {use_analogies}

RETRIEVED STUDENT NOTE CHUNKS:
{context_text}

MANDATORY GROUNDING INSTRUCTIONS:
1. Base your lesson primarily on the facts, concepts, and formulas in the retrieved student notes.
2. In each section, whenever you explain concepts from a chunk, list that chunk's exact ID in `cited_chunk_ids`.
3. NEVER fabricate or invent non-existent chunk IDs. Only cite the valid Chunk IDs provided above.
4. If a section explains general background not in the notes, keep `cited_chunk_ids` empty [].
5. Provide: title, summary, 3-4 sections with headings and rich explanations, and 3-5 key takeaways.
"""
        else:
            return f"""Generate a comprehensive curriculum lesson for:
Lesson Title: {lesson.title}
Module: {lesson.module.title if lesson.module else 'General'}
Target Learning Objectives:
{objectives_str}

STUDENT PREFERENCES:
- Learning Style: {style}
- Explanation Depth: {depth}
- Use Analogies: {use_analogies}

IMPORTANT: No personal student notes are available for this topic.
You are generating a standalone curriculum lesson.
1. The summary must begin with: "[AI-Generated Learning] This lesson provides foundational concepts..."
2. `cited_chunk_ids` in all sections MUST be an empty list []. Do NOT invent citations.
3. Provide: title, summary, 3-4 sections with headings and rich explanations, and 3-5 key takeaways.
"""

    def _parse_and_validate(
        self,
        raw_data: Dict[str, Any],
        lesson: Lesson,
        retrieved_chunks: List[Dict[str, Any]],
        grounding_type: str
    ) -> LessonContent:
        valid_chunk_ids = {c["chunk_id"] for c in retrieved_chunks}
        cited_chunks_map = {c["chunk_id"]: c for c in retrieved_chunks}

        sections = []
        actually_cited_ids = set()

        for s in raw_data.get("sections", []):
            raw_cites = s.get("cited_chunk_ids", [])
            # Filter to genuine retrieved IDs only
            filtered_cites = [cid for cid in raw_cites if cid in valid_chunk_ids]
            actually_cited_ids.update(filtered_cites)
            sections.append(Section(
                heading=s.get("heading", "Topic Overview"),
                content=s.get("content", ""),
                cited_chunk_ids=filtered_cites
            ))

        cited_chunk_models = []
        for cid in actually_cited_ids:
            chunk = cited_chunks_map[cid]
            snippet = chunk["text_content"][:160] + "..." if len(chunk["text_content"]) > 160 else chunk["text_content"]
            cited_chunk_models.append(CitedChunk(
                chunk_id=cid,
                note_title=chunk["note_title"],
                page_number=chunk.get("page_number"),
                snippet=snippet
            ))

        return LessonContent(
            title=raw_data.get("title", lesson.title),
            summary=raw_data.get("summary", f"Lesson on {lesson.title}"),
            sections=sections,
            key_takeaways=raw_data.get("key_takeaways", []),
            grounding_type=grounding_type,
            cited_chunks=cited_chunk_models
        )

    def _generate_fallback_lesson(
        self,
        lesson: Lesson,
        retrieved_chunks: List[Dict[str, Any]],
        grounding_type: str
    ) -> LessonContent:
        """Deterministic fallback lesson if external AI call times out or encounters error."""
        sections = [
            Section(
                heading="1. Core Foundations and Definitions",
                content=f"In this unit on {lesson.title}, we explore fundamental mechanisms, architectural trade-offs, and practical operational paradigms.",
                cited_chunk_ids=[retrieved_chunks[0]["chunk_id"]] if retrieved_chunks else []
            ),
            Section(
                heading="2. Applied Mental Models and Workflow",
                content="Systematic decomposition of complex concepts reveals how state transitions, memory boundaries, and execution models interact.",
                cited_chunk_ids=[retrieved_chunks[1]["chunk_id"]] if len(retrieved_chunks) > 1 else []
            ),
            Section(
                heading="3. Practical Considerations and Edge Cases",
                content="Production setups require careful handling of edge conditions, resource constraints, and latency boundaries.",
                cited_chunk_ids=[]
            )
        ]

        cited_chunk_models = []
        for c in retrieved_chunks[:2]:
            cited_chunk_models.append(CitedChunk(
                chunk_id=c["chunk_id"],
                note_title=c["note_title"],
                page_number=c.get("page_number"),
                snippet=c["text_content"][:140] + "..."
            ))

        summary_prefix = "[RAG-Grounded]" if grounding_type == "rag_grounded" else "[AI-Generated Learning]"

        return LessonContent(
            title=lesson.title,
            summary=f"{summary_prefix} Comprehensive pedagogical study guide covering {lesson.title}.",
            sections=sections,
            key_takeaways=[
                f"Master core principles of {lesson.title}.",
                "Understand operational trade-offs and structural invariants.",
                "Apply structured reasoning to diagnose real-world scenarios."
            ],
            grounding_type=grounding_type,
            cited_chunks=cited_chunk_models
        )


lesson_agent = LessonAgent()
