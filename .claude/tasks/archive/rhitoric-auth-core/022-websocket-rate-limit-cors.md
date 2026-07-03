# 022 — WebSocket rate limiter + CORS header (5.3 + 5.4)

**Status:** [PENDING]
**Phase:** 5
**Group:** ws
**Risk:** LOW
**Effort:** 25m
**Dependencies:** none

## Goal
Add a per-connection sliding-window `MessageRateLimiter`, and allow the `x-token-delivery` CORS request header.

## Context
Merged: the rate limiter is a small standalone utility and the CORS change is a one-liner — grouping avoids a sub-10-minute subtask. `MessageRateLimiter` is per-connection (no shared state). The `X-Token-Delivery: bearer` header (read by the login view in 011) must be allow-listed for cross-origin SPAs. Current `CORS_ALLOW_HEADERS` = `list(default_headers) + ["authorization","content-type"]`.

## Existing pattern to follow
`SRC:utils/websocket/rate_limit.py` — generic, port as-is.

## Files Owned
- `utils/websocket/rate_limit.py` (C)
- `utils/tests/test_ws_rate_limit.py` (C)
- `config/settings/corsheaders.py` (M)

> `utils/websocket/__init__.py` is created by subtask 021 (Phase-5 sibling). If 021 has not run, this subtask MAY create the `__init__.py`; coordinate so exactly one creates it. Prefer: 021 owns `__init__.py`; 022 only adds `rate_limit.py`. If run first, create a minimal `__init__.py`.

## Implementation Steps

### Step 1 — `MessageRateLimiter`
```python
from collections import deque
from time import monotonic

class MessageRateLimiter:
    def __init__(self, max_messages: int = 15, window_seconds: float = 1.0):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._timestamps = deque()
    def is_throttled(self) -> bool:
        now = monotonic()
        while self._timestamps and now - self._timestamps[0] > self.window_seconds:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_messages:
            return True
        self._timestamps.append(now)
        return False
```

### Step 2 — CORS header (`corsheaders.py`)
Append `"x-token-delivery"` to `CORS_ALLOW_HEADERS`.

## Tests (`utils/tests/test_ws_rate_limit.py`)
- 15 rapid `is_throttled()` calls return `False`, the 16th returns `True` (default window).
- After the window elapses (patch/advance `monotonic`, or use a tiny `window_seconds` + real sleep), the limiter allows messages again.
- `from django.conf import settings`: `"x-token-delivery"` in `CORS_ALLOW_HEADERS`.

## Validation
```bash
uv run pytest utils/tests/test_ws_rate_limit.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Sliding-window limiter throttles beyond 15 msg/s and recovers after the window.
- [ ] `x-token-delivery` allow-listed in CORS. Tests pass.
