"""Round 4 regressions (BUG-23 to BUG-29). No database or network needed."""
import asyncio
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import settings
from app.services import groq_client as gc
from app.services.groq_client import GroqClient, GroqClientError


class FakeResp:
    def __init__(self, status, body=None, text="", headers=None):
        self.status_code, self._body, self.text, self.headers = status, body or {}, text, headers or {}

    def json(self):
        return self._body


def fake_http(script):
    calls = []

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, headers=None, json=None, **k):
            calls.append(json["model"])
            return script(json["model"], len(calls))

    return FakeClient, calls


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
    async def no_sleep(*a, **k): return None
    monkeypatch.setattr(gc.asyncio, "sleep", no_sleep)
    c = GroqClient()
    c.api_key = "test-key"
    return c


OK = {"choices": [{"message": {"content": "{}"}}], "usage": {}}
MSGS = [{"role": "user", "content": "hi"}]


async def test_bug23_permanent_error_on_primary_falls_back(client, monkeypatch):
    cls, calls = fake_http(lambda m, n: FakeResp(404, text="model_decommissioned") if m == client.primary_model else FakeResp(200, OK))
    monkeypatch.setattr(gc.httpx, "AsyncClient", cls)
    out = await client.chat_completion(MSGS)
    assert out == OK and calls == [client.primary_model, client.fallback_model]


async def test_bug23_exhaustion_is_retryable_with_status(client, monkeypatch):
    cls, _ = fake_http(lambda m, n: FakeResp(429, headers={"retry-after": "1"}))
    monkeypatch.setattr(gc.httpx, "AsyncClient", cls)
    with pytest.raises(GroqClientError) as ei:
        await client.chat_completion(MSGS)
    assert ei.value.retryable is True and ei.value.status_code == 429
    assert "None" not in str(ei.value)


async def test_bug23_bad_credentials_do_not_try_fallback(client, monkeypatch):
    cls, calls = fake_http(lambda m, n: FakeResp(401, text="bad key"))
    monkeypatch.setattr(gc.httpx, "AsyncClient", cls)
    with pytest.raises(GroqClientError) as ei:
        await client.chat_completion(MSGS)
    assert ei.value.status_code == 401 and len(calls) == 1


async def test_bug23_empty_key_fails_fast(monkeypatch):
    c = GroqClient()
    c.api_key = ""
    with pytest.raises(GroqClientError) as ei:
        await c.chat_completion(MSGS)
    assert ei.value.retryable is False


async def test_bug23_deadline_caps_total_time(client, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_TOTAL_DEADLINE_SECONDS", 0)
    cls, calls = fake_http(lambda m, n: FakeResp(200, OK))
    monkeypatch.setattr(gc.httpx, "AsyncClient", cls)
    with pytest.raises(GroqClientError) as ei:
        await client.chat_completion(MSGS)
    assert ei.value.retryable and not calls


async def test_bug23_bad_json_is_wrapped(client, monkeypatch):
    bad = {"choices": [{"message": {"content": "{not json"}}], "usage": {}}
    cls, _ = fake_http(lambda m, n: FakeResp(200, bad))
    monkeypatch.setattr(gc.httpx, "AsyncClient", cls)
    with pytest.raises(GroqClientError):
        await client.generate_structured_json("x")


def test_bug23_limits_come_from_config():
    assert settings.GROQ_MAX_RPM > 0 and settings.GROQ_MAX_TPM > 0


# ---------------- BUG-24 ----------------
from app.schemas.roadmaps import GoalCreateRequest, PlannedLesson, PlannedModule, RoadmapGenerationOutput
from app.services.roadmap_agent import RoadmapPlanningAgent, RoadmapValidationError, roadmap_agent


def goal(**kw):
    return GoalCreateRequest(subject="Python", total_duration_weeks=kw.pop("weeks", 4), hours_per_week=kw.pop("hpw", 2.0), **kw)


def test_bug24_empty_modules_rejected():
    out = RoadmapGenerationOutput(modules=[])
    with pytest.raises(RoadmapValidationError):
        roadmap_agent._deterministic_sanitize(out, goal())


def test_bug24_sanitizer_repairs_budget_revision_and_future_weeks():
    mod = lambda w, n, mins: PlannedModule(title=f"Module W{w}", description="d", target_week=w, estimated_hours=2,
        lessons=[PlannedLesson(title=f"Lesson {w}-{i}", learning_objectives=["o"], duration_minutes=mins) for i in range(n)])
    out = RoadmapGenerationOutput(modules=[mod(1, 6, 60), mod(3, 2, 30), mod(9, 1, 30)], total_estimated_weeks=4)
    g = goal(weeks=4, hpw=2.0)
    fixed = roadmap_agent._deterministic_sanitize(out, g)
    ok, errs = roadmap_agent.validate_roadmap_rules(fixed, g)
    assert ok, errs
    weeks = {m.target_week for m in fixed.modules}
    assert 9 not in weeks and {1, 2, 3, 4} <= weeks
    assert all(not m.lessons for m in fixed.modules if m.target_week > 2)
    wk1 = [m for m in fixed.modules if m.target_week == 1][0]
    assert sum(l.duration_minutes for l in wk1.lessons) <= 2.0 * 60 * 1.5
    assert any(l.is_revision for m in fixed.modules if m.target_week == 2 for l in m.lessons)


def test_bug24_prompt_is_interpolated():
    import inspect
    src = inspect.getsource(RoadmapPlanningAgent.generate_roadmap)
    assert 'f"3. WEEKLY TIME BUDGET' in src and 'f"6. PEDAGOGY' in src


# ---------------- BUG-25 ----------------
from app.services.lesson_status import normalize_status
from app.services.errors import StepError


def test_bug25_status_vocab():
    assert normalize_status("not_started") == "pending"
    assert normalize_status("completed") == "completed"
    with pytest.raises(StepError):
        normalize_status("bogus")


# ---------------- BUG-27 ----------------
from app.api import rate_limit as rl


def test_bug27_sliding_window_blocks_then_recovers(monkeypatch):
    rl.reset_all()
    for _ in range(3):
        rl._hit("k", 3, 60)
    with pytest.raises(HTTPException) as ei:
        rl._hit("k", 3, 60)
    assert ei.value.status_code == 429 and "Retry-After" in ei.value.headers
    rl._hit("other", 3, 60)  # separate key unaffected


def test_bug27_daily_llm_budget(monkeypatch):
    rl.reset_all()
    monkeypatch.setattr(settings, "USER_DAILY_LLM_CALLS", 2)
    rl._charge_daily_llm("u"); rl._charge_daily_llm("u")
    with pytest.raises(HTTPException) as ei:
        rl._charge_daily_llm("u")
    assert ei.value.status_code == 429


class _Req:
    class client: host = "1.2.3.4"


def test_bug27_login_lockout_and_reset():
    rl.reset_all()
    for _ in range(rl.LOGIN_MAX_FAILURES):
        rl.check_login_allowed("A@x.com", _Req)
        rl.record_login_failure("a@x.com", _Req)
    with pytest.raises(HTTPException):
        rl.check_login_allowed("a@x.com", _Req)
    rl.clear_login_failures("a@x.com", _Req)
    rl.check_login_allowed("a@x.com", _Req)


# ---------------- BUG-28 ----------------
from app.api.sql_utils import escape_like
from app.api.v1.voice import SpeakRequest
from app.api.v1.schedule import GenerateScheduleRequest
from app.schemas.auth import UpdatePreferencesRequest
from app.schemas.lessons import DoubtRequest


def test_bug28_like_escape():
    assert escape_like("100%_a\\b") == "100\\%\\_a\\\\b"


@pytest.mark.parametrize("build", [
    lambda: GoalCreateRequest(subject="x" * 256),
    lambda: GoalCreateRequest(subject="x", preferred_style="s" * 101),
    lambda: GoalCreateRequest(subject="x", current_level="wizard"),
    lambda: UpdatePreferencesRequest(daily_minutes=-5),
    lambda: UpdatePreferencesRequest(daily_minutes=0),
    lambda: UpdatePreferencesRequest(learning_style="s" * 101),
    lambda: DoubtRequest(doubt="d" * 2001),
    lambda: DoubtRequest(doubt=""),
    lambda: SpeakRequest(text="hi", speed=10),
    lambda: SpeakRequest(text="hi", voice="../../etc/passwd"),
    lambda: SpeakRequest(text="x" * 5001),
])
def test_bug28_rejects_bad_input(build):
    with pytest.raises(ValidationError):
        build()


def test_bug28_accepts_good_input():
    SpeakRequest(text="hello", voice="af_heart", speed=1.2)
    UpdatePreferencesRequest(daily_minutes=45, learning_style="visual")
    GoalCreateRequest(subject="Python decorators")
