"""Helpers that keep internal failure details out of HTTP responses.

Full exception text (SQL, driver messages, upstream API bodies) is written to the
server log under a short reference id; the client only receives that id.
"""
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, status


def new_error_reference() -> str:
    return uuid.uuid4().hex[:12]


def internal_error(
    logger: logging.Logger,
    exc: BaseException,
    public_message: str,
    *,
    context: Optional[str] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> HTTPException:
    """Log ``exc`` with a reference id and return an HTTPException with a generic message."""
    ref = new_error_reference()
    logger.error(
        f"[ref={ref}] {context or public_message}: {exc!r}",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return HTTPException(status_code=status_code, detail=f"{public_message} (reference: {ref})")
