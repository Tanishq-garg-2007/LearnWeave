import sys
from pathlib import Path
import pytest

# Ensure backend is on sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.api import rate_limit


@pytest.fixture(autouse=True)
def auto_reset_rate_limits():
    """Reset rate limiting buckets between tests so test suites aren't throttled."""
    rate_limit.reset_all()
    yield
    rate_limit.reset_all()
