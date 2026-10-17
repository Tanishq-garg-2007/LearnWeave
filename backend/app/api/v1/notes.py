import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.sql_utils import escape_like
from app.db.session import get_db
from app.db.models import User, Workspace, Note, NoteChunk
from app.api.deps import get_current_user
from app.api.error_utils import internal_error
from app.schemas.notes import (
    NoteResponse, NoteDetailResponse, NoteUploadResponse, NoteChunkResponse
)
from app.services.document_service import (
    DocumentError,
    document_processor,
    file_type_label,
    raw_preview,
    read_upload_limited,
)
from app.services.embedding_service import embedding_service
from app.services.retrieval_service import retriever

logger = logging.getLogger("learnweave.api.notes")
from app.api.rate_limit import limit_by_ip, limit_by_user

router = APIRouter(prefix="/notes", tags=["Notes & Knowledge Ingestion"])

CHUNK_WORDS = 150
CHUNK_OVERLAP = 30
MAX_TITLE_CHARS = 255  # notes.title is VARCHAR(255)

# Parsing, chunking and embedding are CPU-bound. They run in worker threads, and at most
# this many uploads may hold a processing slot at once, so uploads cannot starve the pool.
INGEST_CONCURRENCY = 2
_ingest_slots = asyncio.Semaphore(INGEST_CONCURRENCY)


def _clean_field(value: str) -> str:
    """Strip NUL characters (PostgreSQL rejects them) and surrounding whitespace."""
    return value.replace("\x00", "").strip()


async def _ingest_document(file_bytes: bytes, filename: str):
    """
    Parse, chunk and embed an upload without blocking the event loop.

    Returns (pages, chunks_meta, embeddings). Document problems are raised as DocumentError.
    Unexpected failures become a generic HTTP error with a reference id.
    """
    async with _ingest_slots:
        try:
            pages = await asyncio.to_thread(
                document_processor.extract_text_with_metadata,
                file_bytes=file_bytes,
                filename=filename,
            )
        except DocumentError:
            raise
        except Exception as exc:
            # A parser crash on malformed input is a client problem, not a server fault.
            raise internal_error(logger, exc, "Unable to read this document", status_code=422) from exc
        if not pages:
            return pages, [], []

        try:
            chunks_meta = await asyncio.to_thread(
                document_processor.chunk_text,
                pages,
                chunk_word_size=CHUNK_WORDS,
                overlap=CHUNK_OVERLAP,
            )
            if not chunks_meta:
                return pages, [], []
            embeddings = await asyncio.to_thread(
                embedding_service.embed_documents,
                [c["text_content"] for c in chunks_meta],
            )
        except DocumentError:
            raise
        except Exception as exc:
            raise internal_error(logger, exc, "Failed to index this document") from exc

    return pages, chunks_meta, embeddings


@router.post("/upload", response_model=NoteUploadResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(limit_by_user('upload', 10, 60))])
async def upload_note(
    file: UploadFile = File(...),
    subject: str = Form(..., min_length=1, max_length=255),
    title: Optional[str] = Form(None, max_length=255),
    tags: Optional[str] = Form("", max_length=500),
    visibility: Optional[str] = Form("private"),
    is_public: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest study document (PDF or plain text), perform semantic chunking,
    generate local 384-dimensional dense embeddings, and index into PostgreSQL pgvector.
    The file type is detected from its content, not from the client's content-type.
    """
    if is_public and str(is_public).lower() in ("true", "1", "yes"):
        visibility = "public"
    filename = _clean_field(file.filename or "uploaded_note.txt") or "uploaded_note.txt"

    try:
        file_bytes = await read_upload_limited(file)
    except DocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message)

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    note_title = (_clean_field(title or "") or filename)[:MAX_TITLE_CHARS]
    subject_clean = _clean_field(subject)
    tag_list = [t for t in (_clean_field(raw) for raw in (tags or "").split(",")) if t]

    try:
        pages, chunks_meta, embeddings = await _ingest_document(file_bytes, filename)
    except DocumentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message)

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the uploaded document"
        )
    if not chunks_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text was too short to generate chunks"
        )

    # Resolve workspace (after processing, so a rejected upload creates nothing)
    res = await db.execute(select(Workspace).where(Workspace.user_id == user.id))
    workspace = res.scalars().first()
    if not workspace:
        workspace = Workspace(user_id=user.id, name=f"{user.email}'s Workspace")
        db.add(workspace)
        await db.flush()

    note = Note(
        owner_id=user.id,
        workspace_id=workspace.id,
        title=note_title,
        subject=subject_clean,
        tags=tag_list,
        raw_content=raw_preview(pages),
        file_type=file_type_label(file_bytes, filename),
        file_size=len(file_bytes),
        visibility="public" if visibility == "public" else "private",
        processing_status="processed"
    )
    db.add(note)
    await db.flush()

    # Store NoteChunks
    for chunk_meta, emb in zip(chunks_meta, embeddings):
        chunk = NoteChunk(
            note_id=note.id,
            owner_id=user.id,
            chunk_index=chunk_meta["chunk_index"],
            text_content=chunk_meta["text_content"],
            page_number=chunk_meta["page_number"],
            embedding=emb
        )
        db.add(chunk)

    await db.commit()

    logger.info(f"Ingested note {note.id} ({note_title}) with {len(chunks_meta)} chunks for user {user.id}")

    return NoteUploadResponse(
        id=note.id,
        title=note.title,
        subject=note.subject,
        chunks_created=len(chunks_meta),
        processing_status=note.processing_status,
        message=f"Successfully indexed {len(chunks_meta)} semantic chunks with 384-d vector embeddings."
    )


@router.get("", response_model=List[NoteResponse])
async def list_notes(
    subject: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List notes uploaded by the current student with chunk counts."""
    # Query notes with chunk counts
    count_subq = (
        select(NoteChunk.note_id, func.count(NoteChunk.id).label("chunk_count"))
        .group_by(NoteChunk.note_id)
        .subquery()
    )

    stmt = (
        select(Note, func.coalesce(count_subq.c.chunk_count, 0).label("chunk_count"))
        .outerjoin(count_subq, Note.id == count_subq.c.note_id)
        .where(Note.owner_id == user.id)
        .order_by(Note.created_at.desc())
    )

    if subject:
        stmt = stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))

    res = await db.execute(stmt)
    rows = res.all()

    output = []
    for note, count in rows:
        output.append(NoteResponse(
            id=note.id,
            title=note.title,
            subject=note.subject,
            tags=note.tags or [],
            file_type=note.file_type or "text/plain",
            file_size=note.file_size or 0,
            visibility=note.visibility,
            processing_status=note.processing_status,
            chunk_count=int(count),
            created_at=note.created_at,
            updated_at=note.updated_at
        ))
    return output


@router.get("/{note_id}", response_model=NoteDetailResponse)
async def get_note_detail(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full details of a note including its indexed chunks."""
    stmt = (
        select(Note)
        .options(selectinload(Note.chunks))
        .where(Note.id == note_id)
    )
    res = await db.execute(stmt)
    note = res.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Access check: owner or public
    if note.owner_id != user.id and note.visibility != "public":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    chunks_data = [
        NoteChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            text_content=c.text_content,
            page_number=c.page_number,
            created_at=c.created_at
        )
        for c in sorted(note.chunks, key=lambda x: x.chunk_index)
    ]

    return NoteDetailResponse(
        id=note.id,
        title=note.title,
        subject=note.subject,
        tags=note.tags or [],
        file_type=note.file_type or "text/plain",
        file_size=note.file_size or 0,
        visibility=note.visibility,
        processing_status=note.processing_status,
        raw_content=note.raw_content,
        chunks=chunks_data,
        created_at=note.created_at,
        updated_at=note.updated_at
    )


@router.delete("/{note_id}", status_code=status.HTTP_200_OK)
async def delete_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a note and cascade delete its chunks."""
    res = await db.execute(select(Note).where(Note.id == note_id))
    note = res.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete notes owned by others")

    await db.delete(note)
    await db.commit()
    return {"status": "success", "message": "Note deleted successfully", "id": note_id}


@router.post("/search", dependencies=[Depends(limit_by_user('search', 60, 60))])
async def search_notes(
    query: str,
    subject: Optional[str] = None,
    top_k: int = Query(4, ge=1, le=20, description="Number of results, from 1 to 20"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct hybrid RAG search endpoint for testing and retrieval verification.
    Combines dense vector search and sparse FTS via RRF (k=60).
    """
    # The first embedding call loads the model, which can take seconds. Load it in a worker
    # thread so the event loop keeps serving other users. Later calls return immediately.
    await asyncio.to_thread(embedding_service.warm_up)

    results = await retriever.retrieve(
        db=db,
        query=query,
        user_id=user.id,
        top_k=top_k,
        subject=subject
    )
    return {"query": query, "count": len(results), "results": results}
