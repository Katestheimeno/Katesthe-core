# 016 — Session revocation service (3.1)

**Status:** [PENDING]
**Phase:** 3
**Group:** sess
**Risk:** HIGH
**Effort:** 45m
**Dependencies:** Phase 2 complete (011 — cookie auth in place for the logout flow)

## Goal
Create `accounts/services/session.py` with `revoke_all_sessions()` (blacklist all outstanding refresh tokens + set a revocation cache key) and `detect_refresh_reuse()` (token-family revocation on replay).

## Context
`accounts/services/` exists (empty `__init__.py`). `rest_framework_simplejwt.token_blacklist` is installed (`OutstandingToken`/`BlacklistedToken`). The cache key `auth:revoked_after:{user_id}` is a CONTRACT consumed by the WS middleware (020) — keep the string identical.

## Existing pattern to follow
`SRC:accounts/services/session.py` — generic, port as-is.

## Files Owned
- `accounts/services/session.py` (C)
- `accounts/tests/services/test_session.py` (C)

## Implementation Steps

### Step 1 — `revoke_all_sessions(user_id: int, event: str) -> int`
- Query `OutstandingToken.objects.filter(user_id=user_id, expires_at__gt=now())`.
- Blacklist via `BlacklistedToken.objects.bulk_create([BlacklistedToken(token=t) for t in ...], ignore_conflicts=True)`; count newly created rows.
- Set cache key `f"auth:revoked_after:{user_id}"` = `int(now().timestamp())` with a 7-day TTL (`60*60*24*7`). **Type contract with 020:** store an integer unix seconds; the WS middleware (020) compares the token `iat` (also integer seconds) with `token_iat < revoked_after`. Keep both sides integer seconds so the comparison is exact (SRC uses `time.time()` float — normalize to `int` here and document it in the 016↔020 contract).
- Log `logger.bind(event=event, user_id=user_id, tokens_revoked=count).info("auth.sessions_revoked")` (import `from config.logger import logger`).
- Return the count.

### Step 2 — `detect_refresh_reuse(raw_token: str) -> None`
- Parse `RefreshToken(raw_token)` — this validates signature + expiry. Wrap in try/except `TokenError`; on failure RETURN silently (garbage/forged/expired tokens are NOT reuse).
- Only after successful verification, read `jti`/`user_id` from the validated payload. If a `BlacklistedToken` already exists for that `jti` (i.e., the token was rotated/blacklisted yet is being replayed), call `revoke_all_sessions(user_id, event="refresh_reuse")` and log `logger.bind(user_id=...).warning("refresh.reuse_detected")`.

## Tests (`accounts/tests/services/test_session.py`)
- `@pytest.mark.django_db`: create N outstanding tokens for a user (`RefreshToken.for_user`), call `revoke_all_sessions` → returns N, all blacklisted, cache key set to a plausible timestamp.
- Calling again returns 0 (idempotent via `ignore_conflicts`).
- `detect_refresh_reuse` with a forged/garbage/expired token → no-op (no revocation, no raise).
- `detect_refresh_reuse` with a valid-but-already-blacklisted refresh token → triggers `revoke_all_sessions` (assert cache key set / other sessions blacklisted).

## Validation
```bash
uv run pytest accounts/tests/services/test_session.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `revoke_all_sessions` blacklists outstanding tokens + sets `auth:revoked_after:{user_id}` (7-day TTL) + returns count.
- [ ] `detect_refresh_reuse` only acts on fully-verified replayed tokens; ignores invalid ones.
- [ ] Tests pass.
