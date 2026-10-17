import logging
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.sql_utils import escape_like
from app.db.session import get_db
from app.db.models import User, Workspace, Note, NoteChunk, NoteVote, NoteReport
from app.api.deps import get_current_user
from app.api.error_utils import internal_error
from app.services.wilson_service import update_note_wilson_score

QUARANTINE_THRESHOLD = 3  # distinct reporting accounts needed to quarantine a public note
QUARANTINED_VISIBILITY = "reported_quarantine"

logger = logging.getLogger("learnweave.api.community")
router = APIRouter(prefix="/community", tags=["Community Library & Moderation"])


class VoteRequest(BaseModel):
    vote_value: int = Field(..., description="+1 for upvote, -1 for downvote")


class ReportRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class PublishRequest(BaseModel):
    visibility: str = Field(..., description="'public' or 'private'")


class CommunityNoteResponse(BaseModel):
    id: str
    title: str
    subject: str
    tags: List[str] = Field(default_factory=list)
    file_type: str
    file_size: int
    visibility: str
    wilson_score: float
    upvotes: int
    downvotes: int
    chunk_count: int
    is_imported: bool
    source_note_id: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/notes", response_model=Dict[str, Any])
async def list_community_notes(
    query: Optional[str] = Query(None, max_length=200),
    subject: Optional[str] = Query(None, max_length=255),
    tag: Optional[str] = Query(None, max_length=50),
    sort_by: Literal["wilson", "latest", "upvotes"] = "wilson",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Discover public study notes in the global community library.
    Ranked by Wilson score confidence interval or recency.
    Quarantined notes are automatically excluded.
    """
    # Subqueries for votes and chunk counts
    upvote_subq = (
        select(NoteVote.note_id, func.count(NoteVote.id).label("upvotes"))
        .where(NoteVote.vote_value == 1)
        .group_by(NoteVote.note_id)
        .subquery()
    )
    downvote_subq = (
        select(NoteVote.note_id, func.count(NoteVote.id).label("downvotes"))
        .where(NoteVote.vote_value == -1)
        .group_by(NoteVote.note_id)
        .subquery()
    )
    chunk_subq = (
        select(NoteChunk.note_id, func.count(NoteChunk.id).label("chunk_count"))
        .group_by(NoteChunk.note_id)
        .subquery()
    )

    stmt = (
        select(
            Note,
            func.coalesce(upvote_subq.c.upvotes, 0).label("upvotes"),
            func.coalesce(downvote_subq.c.downvotes, 0).label("downvotes"),
            func.coalesce(chunk_subq.c.chunk_count, 0).label("chunk_count")
        )
        .outerjoin(upvote_subq, Note.id == upvote_subq.c.note_id)
        .outerjoin(downvote_subq, Note.id == downvote_subq.c.note_id)
        .outerjoin(chunk_subq, Note.id == chunk_subq.c.note_id)
        .where(Note.visibility == "public")
    )

    if subject:
        stmt = stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))

    if query:
        stmt = stmt.where(
            or_(
                Note.title.ilike(f"%{escape_like(query)}%", escape="\\"),
                Note.raw_content.ilike(f"%{escape_like(query)}%", escape="\\")
            )
        )

    # Sort
    if sort_by == "latest":
        stmt = stmt.order_by(Note.created_at.desc())
    elif sort_by == "upvotes":
        stmt = stmt.order_by(desc("upvotes"))
    else:  # Default wilson
        stmt = stmt.order_by(Note.wilson_score.desc(), Note.created_at.desc())

    # Total count
    count_stmt = select(func.count(Note.id)).where(Note.visibility == "public")
    if subject:
        count_stmt = count_stmt.where(Note.subject.ilike(f"%{escape_like(subject)}%", escape="\\"))
    if query:
        count_stmt = count_stmt.where(or_(Note.title.ilike(f"%{escape_like(query)}%", escape="\\"), Note.raw_content.ilike(f"%{escape_like(query)}%", escape="\\")))
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()

    notes_data = []
    for note, upvotes, downvotes, chunk_count in rows:
        notes_data.append(CommunityNoteResponse(
            id=note.id,
            title=note.title,
            subject=note.subject,
            tags=note.tags or [],
            file_type=note.file_type or "text/plain",
            file_size=note.file_size or 0,
            visibility=note.visibility,
            wilson_score=note.wilson_score or 0.0,
            upvotes=int(upvotes),
            downvotes=int(downvotes),
            chunk_count=int(chunk_count),
            is_imported=note.is_imported or False,
            source_note_id=note.source_note_id,
            created_at=note.created_at.isoformat() if note.created_at else None
        ))

    return {
        "total": total_count,
        "offset": offset,
        "limit": limit,
        "notes": notes_data
    }


@router.post("/notes/{note_id}/vote")
async def vote_note(
    note_id: str,
    req: VoteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cast an upvote (+1) or downvote (-1) on a public community note.
    Voting the same value again removes the vote. Owners cannot vote on their own notes.
    The vote, the counts and the Wilson score are written in one transaction.
    """
    if req.vote_value not in (-1, 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vote_value must be exactly +1 (upvote) or -1 (downvote)"
        )

    # Lock the note row: votes on the same note are serialized, so counts cannot be lost.
    n_res = await db.execute(select(Note).where(Note.id == note_id).with_for_update())
    note = n_res.scalar_one_or_none()
    if not note or note.visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot vote on your own note")

    v_res = await db.execute(
        select(NoteVote).where(NoteVote.note_id == note_id, NoteVote.user_id == user.id)
    )
    existing_vote = v_res.scalar_one_or_none()

    try:
        if existing_vote:
            if existing_vote.vote_value == req.vote_value:
                await db.delete(existing_vote)  # same button again removes the vote
            else:
                existing_vote.vote_value = req.vote_value
        else:
            db.add(NoteVote(user_id=user.id, note_id=note_id, vote_value=req.vote_value))

        # Session autoflush is off: flush so the aggregate below sees this vote.
        await db.flush()
        new_wilson = await update_note_wilson_score(db, note_id, note=note)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise internal_error(
            logger, exc, "Vote could not be recorded, please retry",
            status_code=status.HTTP_409_CONFLICT,
        )

    counts_res = await db.execute(
        select(NoteVote.vote_value, func.count(NoteVote.id))
        .where(NoteVote.note_id == note_id)
        .group_by(NoteVote.vote_value)
    )
    counts = {int(value): int(count) for value, count in counts_res.all()}
    upvotes = counts.get(1, 0)
    downvotes = counts.get(-1, 0)

    return {
        "note_id": note_id,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "wilson_score": new_wilson,
        "new_wilson_score": new_wilson,
        "message": "Vote recorded and Wilson score updated."
    }


@router.post("/notes/{note_id}/import")
async def import_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import a public note into the student's personal workspace.
    Creates an independent deep copy of the note and all vector chunks.
    Ensures subsequent modifications/deletion of the original do not affect the clone.
    """
    # Fetch source note with chunks
    res = await db.execute(
        select(Note).options(selectinload(Note.chunks)).where(Note.id == note_id)
    )
    source_note = res.scalar_one_or_none()
    if not source_note or source_note.visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source note not found")

    if source_note.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already own this note")

    # Get student workspace
    w_res = await db.execute(select(Workspace).where(Workspace.user_id == user.id))
    workspace = w_res.scalars().first()
    if not workspace:
        workspace = Workspace(user_id=user.id, name=f"{user.email}'s Workspace")
        db.add(workspace)
        await db.flush()

    # Create deep clone
    cloned_note = Note(
        owner_id=user.id,
        workspace_id=workspace.id,
        title=f"{source_note.title} (Imported)",
        subject=source_note.subject,
        tags=list(source_note.tags or []),
        raw_content=source_note.raw_content,
        file_type=source_note.file_type,
        file_size=source_note.file_size,
        visibility="private",
        processing_status="processed",
        is_imported=True,
        source_note_id=source_note.id,
        source_version=1
    )
    db.add(cloned_note)
    await db.flush()

    # Clone chunks with new owner_id
    cloned_chunks = []
    for sc in source_note.chunks:
        chunk = NoteChunk(
            note_id=cloned_note.id,
            owner_id=user.id,
            chunk_index=sc.chunk_index,
            text_content=sc.text_content,
            page_number=sc.page_number,
            embedding=sc.embedding
        )
        db.add(chunk)
        cloned_chunks.append(chunk)

    await db.commit()
    await db.refresh(cloned_note)

    logger.info(f"User {user.id} imported note {source_note.id} as new independent note {cloned_note.id}")

    return {
        "status": "imported",
        "imported_note_id": cloned_note.id,
        "new_note_id": cloned_note.id,
        "title": cloned_note.title,
        "chunks_imported": len(cloned_chunks),
        "source_note_id": source_note.id,
        "message": f"Successfully imported '{cloned_note.title}' into your private workspace."
    }


@router.post("/notes/{note_id}/report")
async def report_note(
    note_id: str,
    req: ReportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Report inappropriate or violating public note content.
    Each account can report a note once. When QUARANTINE_THRESHOLD distinct accounts have
    reported it, the note is quarantined and cannot be republished by its owner.
    """
    # Lock the note row so concurrent reports are counted exactly once each.
    res = await db.execute(select(Note).where(Note.id == note_id).with_for_update())
    note = res.scalar_one_or_none()
    if not note or note.visibility not in ("public", QUARANTINED_VISIBILITY):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot report your own note")

    dup_res = await db.execute(
        select(NoteReport.id).where(NoteReport.note_id == note.id, NoteReport.reporter_id == user.id)
    )
    if dup_res.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reported this note")

    report = NoteReport(
        reporter_id=user.id,
        note_id=note.id,
        reason=req.reason.strip(),
        status="pending"
    )
    db.add(report)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already reported this note")

    # Count distinct reporting accounts, not rows.
    cnt_res = await db.execute(
        select(func.count(func.distinct(NoteReport.reporter_id))).where(
            NoteReport.note_id == note.id,
            NoteReport.status == "pending"
        )
    )
    report_count = int(cnt_res.scalar() or 0)

    quarantined = False
    if report_count >= QUARANTINE_THRESHOLD and note.visibility == "public":
        note.visibility = QUARANTINED_VISIBILITY
        quarantined = True
        logger.warning(f"Note {note.id} reached {report_count} distinct reporters. Quarantining.")

    await db.commit()

    return {
        "note_id": note_id,
        "total_reports": report_count,
        "quarantined": quarantined or note.visibility == QUARANTINED_VISIBILITY,
        "message": "Report logged. Content quarantined from public library." if quarantined else "Report received for moderation review."
    }


@router.put("/notes/{note_id}/publish")
async def publish_or_privatize_note(
    note_id: str,
    req: PublishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish a personal note to the community or withdraw it to private.

    Quarantined notes cannot be changed by the owner while under moderation.
    """
    if req.visibility not in ("public", "private"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visibility must be 'public' or 'private'")

    res = await db.execute(select(Note).where(Note.id == note_id))
    note = res.scalar_one_or_none()
    if not note or note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.visibility == QUARANTINED_VISIBILITY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This note is quarantined after community reports and cannot be changed"
        )

    note.visibility = req.visibility
    await db.commit()
    return {"id": note.id, "visibility": note.visibility, "message": f"Note is now {note.visibility}."}
