"""In-process sliding-window rate limits (BUG-27).

Per-process state: with several workers each has its own counters, so the effective
limit is N x the configured one. Swap `_store` for Redis if you scale horizontally.
"""
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict

from fastapi import Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.config import settings
from app.db.models import User

_store: Dict[str, Deque[float]] = defaultdict(deque)
_failed_logins: Dict[str, Deque[float]] = defaultdict(deque)
_daily_llm: Dict[str, list] = {}  # key -> [window_start, count]

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _hit(key: str, limit: int, window: int) -> None:
    now = time.monotonic()
    q = _store[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        retry = max(1, int(window - (now - q[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
            headers={"Retry-After": str(retry)},
        )
    q.append(now)


def limit_by_ip(name: str, limit: int, window: int = 60) -> Callable:
    async def dep(request: Request) -> None:
        if settings.RATE_LIMIT_ENABLED:
            _hit(f"ip:{name}:{_client_ip(request)}", limit, window)
    return dep


def limit_by_user(name: str, limit: int, window: int = 60, llm: bool = False) -> Callable:
    async def dep(user: User = Depends(get_current_user)) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        _hit(f"user:{name}:{user.id}", limit, window)
        if llm:
            _charge_daily_llm(user.id)
    return dep


def _charge_daily_llm(user_id: str) -> None:
    now = time.time()
    entry = _daily_llm.get(user_id)
    if entry is None or now - entry[0] > 86400:
        entry = _daily_llm[user_id] = [now, 0]
    if entry[1] >= settings.USER_DAILY_LLM_CALLS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI usage limit reached. Please try again tomorrow.",
            headers={"Retry-After": "3600"},
        )
    entry[1] += 1


# ---- login lockout (keyed by email + IP so an attacker cannot lock out the real owner from elsewhere)
def _login_key(email: str, request: Request) -> str:
    return f"{email.lower()}|{_client_ip(request)}"


def check_login_allowed(email: str, request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    now = time.monotonic()
    q = _failed_logins[_login_key(email, request)]
    while q and now - q[0] > LOGIN_WINDOW_SECONDS:
        q.popleft()
    if len(q) >= LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Try again later.",
            headers={"Retry-After": str(int(LOGIN_WINDOW_SECONDS - (now - q[0])) + 1)},
        )


def record_login_failure(email: str, request: Request) -> None:
    _failed_logins[_login_key(email, request)].append(time.monotonic())


def clear_login_failures(email: str, request: Request) -> None:
    _failed_logins.pop(_login_key(email, request), None)


def reset_all() -> None:  # for tests
    _store.clear(); _failed_logins.clear(); _daily_llm.clear()
