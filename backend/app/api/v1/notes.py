import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import User, Workspace, Note, NoteChunk
from app.api.deps import get_current_user
from app.schemas.notes import (
    NoteResponse, NoteDetailResponse, NoteUploadResponse, NoteChunkResponse
)
from app.services.document_service import document_processor
from app.services.embedding_service import embedding_service
from app.services.retrieval_service import retriever

logger = logging.getLogger("learnweave.api.notes")
router = APIRouter(prefix="/notes", tags=["Notes & Knowledge Ingestion"])


@router.post("/upload", response_model=NoteUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_note(
    file: UploadFile = File(...),
    subject: str = Form(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(""),
    visibility: Optional[str] = Form("private"),
    is_public: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest study document (PDF, Markdown, TXT), perform semantic chunking,
    generate local 384-dimensional dense embeddings, and index into PostgreSQL pgvector.
    """
    if is_public and str(is_public).lower() in ("true", "1", "yes"):
        visibility = "public"
    filename = file.filename or "uploaded_note.txt"
    content_type = file.content_type or "text/plain"

    file_bytes = await file.read()
    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    # 25 MB limit
    if len(file_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum permitted limit of 25MB"
        )

    note_title = title.strip() if title and title.strip() else filename

    # Resolve workspace
    res = await db.execute(select(Workspace).where(Workspace.user_id == user.id))
    workspace = res.scalars().first()
    if not workspace:
        workspace = Workspace(user_id=user.id, name=f"{user.email}'s Workspace")
        db.add(workspace)
        await db.flush()

    # Process and extract text
    try:
        pages = document_processor.extract_text_with_metadata(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type
        )
    except Exception as exc:
        logger.error(f"Failed to extract text from {filename}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to process document format: {exc}"
        )

    if not pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No readable text could be extracted from the uploaded document"
        )

    # Chunk text
    chunks_meta = document_processor.chunk_text(pages, chunk_word_size=150, overlap=30)
    if not chunks_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text was too short to generate chunks"
        )

    # Generate embeddings
    chunk_texts = [c["text_content"] for c in chunks_meta]
    embeddings = embedding_service.embed_documents(chunk_texts)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # Store Note
    raw_preview = file_bytes[:10000].decode("utf-8", errors="replace")
    note = Note(
        owner_id=user.id,
        workspace_id=workspace.id,
        title=note_title,
        subject=subject.strip(),
        tags=tag_list,
        raw_content=raw_preview,
        file_type=content_type,
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
        stmt = stmt.where(Note.subject.ilike(f"%{subject}%"))

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


@router.post("/search")
async def search_notes(
    query: str,
    subject: Optional[str] = None,
    top_k: int = 4,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct hybrid RAG search endpoint for testing and retrieval verification.
    Combines dense vector search and sparse FTS via RRF (k=60).
    """
    results = await retriever.retrieve(
        db=db,
        query=query,
        user_id=user.id,
        top_k=top_k,
        subject=subject
    )
    return {"query": query, "count": len(results), "results": results}
