import math
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models import NoteVote, Note

logger = logging.getLogger("learnweave.wilson")


def calculate_wilson_score(upvotes: int, downvotes: int, confidence: float = 0.95) -> float:
    """
    Calculate the lower bound of Wilson score confidence interval for a Bernoulli parameter.
    Used for statistically sound community ranking (avoids small-sample bias).
    """
    n = upvotes + downvotes
    if n == 0:
        return 0.0

    # z-score for 95% confidence is 1.95996
    z = 1.95996 if confidence >= 0.95 else 1.64485
    p_hat = upvotes / n

    numerator = p_hat + (z * z) / (2 * n) - z * math.sqrt((p_hat * (1 - p_hat) + (z * z) / (4 * n)) / n)
    denominator = 1 + (z * z) / n

    score = numerator / denominator
    return max(0.0, min(1.0, round(score, 4)))


async def update_note_wilson_score(db: AsyncSession, note_id: str, note: Note = None) -> float:
    """Recompute the Wilson score from one aggregate query and store it on the note.

    Does NOT commit: the caller owns the transaction, so the vote write and the score
    update succeed or fail together.
    """
    rows = await db.execute(
        select(NoteVote.vote_value, func.count(NoteVote.id))
        .where(NoteVote.note_id == note_id)
        .group_by(NoteVote.vote_value)
    )
    counts = {int(value): int(count) for value, count in rows.all()}
    score = calculate_wilson_score(counts.get(1, 0), counts.get(-1, 0))

    if note is None:
        note_res = await db.execute(select(Note).where(Note.id == note_id))
        note = note_res.scalar_one_or_none()
    if note is not None:
        note.wilson_score = score
        await db.flush()

    return score
