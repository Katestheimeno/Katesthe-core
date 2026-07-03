# Rhitoric Auth Core Backport (Phases 1–5)

Priority: P1
Status: active
**Date:** 2026-07-03
**Source:** `RHITORIC_BACKPORT_PLAN.md` (repo root) — Phases 1–5 + the "What NOT to Do" section. Backport RS256 JWT, HttpOnly-cookie auth with CSRF, session revocation/replay-detection, the full throttle-class architecture, and WebSocket JWT auth infrastructure from `Rhitoric-core` (SRC) into this template (DST). Generic patterns only.
**Goal:** This template's auth is RS256 (asymmetric, with JWKS + `kid`), supports HttpOnly-cookie transport with CSRF enforcement and a `X-Token-Delivery: bearer` opt-out, revokes all sessions on privilege change / logout-all with refresh-reuse detection, ships the ~14 universal throttle classes with a global toggle, and authenticates WebSocket connections via JWT — all generic (no game/AI/elearning logic), all tested, full suite + OpenAPI validation green.

**Reference convention:** `SRC:path` = `/home/tmpusr/Documents/github/Rhitoric-core/path`; `DST:path` = `/home/tmpusr/dev/Katesthe-core/path`.

**Sibling active features (coordinated split of the same backport plan):** `rhitoric-utilities` (Phases 6–11 + scaffold) and `rhitoric-notification-system` (Phase 12). See **Active feature conflicts** below — three genuine shared-file hazards require cross-feature serialization.

---

## Locked decisions

1. **Scope = plan Phases 1–5 only** (items 1.1–1.7, 2.1–2.6, 3.1–3.4, 4.1–4.3, 5.1–5.4). Phases 6–12 are OUT of scope (owned by the sibling features).
2. **Extract GENERIC patterns only.** Obey ALL 18 items in the plan's "What NOT to Do" section: no game/AI/elearning domain logic; no domain-specific throttles/permissions/consumers/beat entries; strip `console.log`; **RS256 is required, not optional**; auth cookies default to `SameSite=Lax`; do NOT add `JWT_RSA_PREVIOUS_PUBLIC_KEY` to `.env.local.example`; liveness/email use `settings.PROJECT_NAME` / `settings.DEFAULT_FROM_EMAIL`, never hardcoded Rhitoric values. Strip the `_token.py` deleted-user / `days_remaining` branch and the `admin_api.`-prefix permission gymnastics.
3. **RS256 migration is an APPROVED breaking change**, including rewriting existing auth tests/factories. Current state is HS256 with `settings.JWT_SECRET_KEY` in `config/settings/restframework.py`. Subtask **023** owns updating the existing auth tests/fixtures/factories.
4. **`INSTALLED_APPS`/`MIDDLEWARE` live in `config/settings/apps_middlewares.py`.** New env-var fields go in the Pydantic `MainSettings` class in `config/settings/config.py`. No new `config/settings/<name>.py` module is created in this feature, so `config/settings/__init__.py` is NOT touched.
5. **`errors/catalog.py` is NOT touched.** Existing `AUTH__*` / `PERMISSION__*` codes cover every path here (CSRF failure → DRF `PermissionDenied` → `PERMISSION__DENIED`; WS auth failure → `AUTH__TOKEN_INVALID`). Do not invent new codes. (This also keeps `errors/catalog.py` free for the notification-system feature, which DOES own it.)
6. **`kid` tokens are actually wired into issuance.** Subtask 004 creates `accounts/tokens.py` AND sets `token_class = KidRefreshToken` on the obtain serializer + a `KidTokenRefreshSerializer` (in `_token.py`) + `serializer_class` on the refresh view (in `_auth.py`), so login/refresh emit `kid`-headed tokens that JWKS consumers can verify.
7. **Default login response = cookies, not body tokens.** The login view sets HttpOnly cookies and returns tokens in the body ONLY when the request carries `X-Token-Delivery: bearer`. This is a deliberate breaking change; 023 reconciles the ~80 affected assertions.
8. **`PyJWT` and `kombu` are NOT added by this feature.** `cryptography` IS added by subtask 001 (plan "What NOT to Do" #8). `PyJWT` already ships transitively with `djangorestframework-simplejwt`. `kombu` is added by the SIBLING feature rhitoric-utilities/006.
9. **`config/settings/celery.py` is OWNED by rhitoric-utilities/006, NOT by this feature.** Subtask 017 creates the `flush_expired_jwt_tokens` task by name only; utilities/006 adds its beat entry by string.

---

## Priority queue

| ID | Subtask | Phase | Group | Risk | Effort | Scope |
|----|---------|-------|-------|------|--------|-------|
| 001 | RSA key management module (1.1) | 1 | core | MED | 30m | `config/jwt_keys.py`, `pyproject.toml` (+cryptography) |
| 002 | Pydantic settings — JWT/Cookie/Throttle (1.2) | 1 | core | LOW | 25m | `config/settings/config.py` |
| 003 | SimpleJWT RS256 configuration (1.3) | 1 | core | HIGH | 40m | `config/settings/restframework.py` (owner #1) |
| 004 | Kid token classes + issuance wiring (1.4) | 1 | core | MED | 35m | `accounts/tokens.py`, `_token.py` (P1), `_auth.py` (P1) |
| 005 | `generate_jwt_keys` command (1.5) | 1 | cmd | LOW | 20m | `accounts/management/commands/` |
| 006 | JWKS endpoint (1.6) | 1 | tail | MED | 35m | `accounts/controllers/_jwks.py`, `urls/_auth.py`, `controllers/__init__.py` |
| 007 | Production RS256 enforcement + env examples (1.7) | 1 | prod | LOW | 25m | `config/django/production.py` (owner #1), `.env.*.example` |
| 008 | Throttle base classes (4.1) | 4 | thr | MED | 45m | `utils/throttles.py` |
| 009 | Throttle rates in REST_FRAMEWORK (4.2) | 4 | thr | LOW | 15m | `config/settings/restframework.py` (owner #2) |
| 010 | Flush-throttles command (4.3) | 4 | thr | LOW | 20m | `utils/management/commands/flush_throttles.py` |
| 011 | Cookie JWT authentication (2.1) | 2 | auth | HIGH | 55m | `accounts/authentication.py`, `restframework.py` (owner #3), `_auth.py` (P2) |
| 012 | Spectacular auth extension (2.2) | 2 | auth | LOW | 20m | `config/spectacular_auth.py`, `config/settings/spectacular.py` |
| 013 | Security-headers + liveness middleware (2.3+2.6) | 2 | mw | MED | 40m | `config/middleware/{security_headers,liveness_probe}.py`, `apps_middlewares.py` |
| 014 | Enhanced production security (2.4) | 2 | prod | LOW | 25m | `config/django/production.py` (owner #2), `config/django/base.py` |
| 015 | Timing-oracle defense in login (2.5) | 2 | tok | LOW | 20m | `accounts/serializers/auth/_token.py` (P2) |
| 016 | Session revocation service (3.1) | 3 | sess | HIGH | 45m | `accounts/services/session.py` |
| 017 | Token housekeeping task + tasks package (3.2) | 3 | task | MED | 35m | `accounts/tasks/` package (task name only — NOT celery.py) |
| 018 | Custom JWT claims — is_superuser exclusion (3.3) | 3 | tok | MED | 30m | `accounts/serializers/auth/_token.py` (P3) |
| 019 | Privilege-change session revocation (3.4) | 3 | sess | HIGH | 60m | `accounts/controllers/_auth.py` (P3) + `accounts/urls/_auth.py` (2nd owner, after 006) |
| 020 | JWT WebSocket auth middleware (5.1) | 5 | ws | HIGH | 55m | `utils/middleware/`, `config/asgi.py` |
| 021 | WebSocket protocol utilities (5.2) | 5 | ws | MED | 40m | `utils/websocket/protocol.py` |
| 022 | WebSocket rate limiter + CORS header (5.3+5.4) | 5 | ws | LOW | 25m | `utils/websocket/rate_limit.py`, `config/settings/corsheaders.py` |
| 023 | Update existing auth tests/factories → RS256 + cookies | 3 | test | HIGH | 60m | `accounts/tests/{controllers,serializers}/test_auth.py`, `conftest.py`, `factories/_user.py` |
| 024 | Feature validation gate (full suite + OpenAPI) | 6 | — | LOW | 20m | `.coveragerc` (last-mile omits only) |

---

## Subtasks

<!-- Canonical status list. The orchestrator flips these to [COMPLETED]; archive reads them. -->
<!-- Status token: PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED -->
- [PENDING] [001-rsa-key-module.md](001-rsa-key-module.md) — RSA key management module (1.1)
- [PENDING] [002-pydantic-settings.md](002-pydantic-settings.md) — Pydantic settings JWT/Cookie/Throttle fields (1.2)
- [PENDING] [003-rs256-simplejwt-config.md](003-rs256-simplejwt-config.md) — SimpleJWT RS256 configuration (1.3)
- [PENDING] [004-kid-token-classes.md](004-kid-token-classes.md) — Kid token classes + issuance wiring (1.4)
- [PENDING] [005-generate-jwt-keys-command.md](005-generate-jwt-keys-command.md) — generate_jwt_keys management command (1.5)
- [PENDING] [006-jwks-endpoint.md](006-jwks-endpoint.md) — JWKS endpoint (1.6)
- [PENDING] [007-production-rs256-enforcement.md](007-production-rs256-enforcement.md) — Production RS256 enforcement + env examples (1.7)
- [PENDING] [008-throttle-base-classes.md](008-throttle-base-classes.md) — Throttle base classes (4.1)
- [PENDING] [009-throttle-rates.md](009-throttle-rates.md) — Throttle rates in REST_FRAMEWORK (4.2)
- [PENDING] [010-flush-throttles-command.md](010-flush-throttles-command.md) — Flush-throttles command (4.3)
- [PENDING] [011-cookie-jwt-authentication.md](011-cookie-jwt-authentication.md) — Cookie JWT authentication (2.1)
- [PENDING] [012-spectacular-auth-extension.md](012-spectacular-auth-extension.md) — Spectacular auth extension (2.2)
- [PENDING] [013-security-liveness-middleware.md](013-security-liveness-middleware.md) — Security-headers + liveness middleware (2.3+2.6)
- [PENDING] [014-enhanced-production-security.md](014-enhanced-production-security.md) — Enhanced production security (2.4)
- [PENDING] [015-timing-oracle-defense.md](015-timing-oracle-defense.md) — Timing-oracle defense in login (2.5)
- [PENDING] [016-session-revocation-service.md](016-session-revocation-service.md) — Session revocation service (3.1)
- [PENDING] [017-token-housekeeping-task.md](017-token-housekeeping-task.md) — Token housekeeping task + tasks package (3.2)
- [PENDING] [018-custom-jwt-claims.md](018-custom-jwt-claims.md) — Custom JWT claims / is_superuser exclusion (3.3)
- [PENDING] [019-privilege-change-revocation.md](019-privilege-change-revocation.md) — Privilege-change session revocation (3.4)
- [PENDING] [020-jwt-websocket-middleware.md](020-jwt-websocket-middleware.md) — JWT WebSocket auth middleware (5.1)
- [PENDING] [021-websocket-protocol-utils.md](021-websocket-protocol-utils.md) — WebSocket protocol utilities (5.2)
- [PENDING] [022-websocket-rate-limit-cors.md](022-websocket-rate-limit-cors.md) — WebSocket rate limiter + CORS header (5.3+5.4)
- [PENDING] [023-update-auth-tests.md](023-update-auth-tests.md) — Update existing auth tests/factories → RS256 + cookies
- [PENDING] [024-validation-gate.md](024-validation-gate.md) — Feature validation gate

---

## Dependency graph

```
PHASE 1 (RS256 foundation) + PHASE 4 (throttles) run CONCURRENTLY.

  core chain:  001 ─► 002 ─► 003 ─► 004
                        │       │      └─(P1 owner of _token.py, _auth.py)
                        │       └─(restframework owner #1)
                        │
  cmd:   001 ─► 005
  prod:  002 ─► 007
  P4:    008 ─► 009            010 (independent, start anytime)
  tail:  {003, 004, 008} ─► 006   (JWKS needs RS256 config + kid tokens + PublicListThrottle)

  restframework.py serialize:  003 ─► 009 ─► 011   (three owners, fully sequential)

PHASE 2 (cookie auth) — after ALL of Phase 1 (and 009) complete:
  011 ─► 012                          (011 needs 003+009; owns _auth.py after 004)
  013 (independent)   014 (needs 007) 015 (needs 004; owns _token.py after 004)

PHASE 3 (session mgmt) — after ALL of Phase 2 complete:
  016 (needs 011)     017 (independent)     018 (needs 004+015; _token.py chain)
  019 (needs 011+016+006; _auth.py chain + urls chain after 006)
  023 (needs 011+015+018+019) ── LAST in Phase 3 (test reconciliation)

PHASE 5 (websocket) — after Phase 1 + Phase 3:
  020 (needs 003+016)   021 (independent)   022 (independent)
  (Phase 5 may run concurrently with 023 — disjoint files.)

FINAL GATE:
  024 — after every code + test subtask.
```

**Concurrency summary**
- P1+P4 window: peak ~5 lanes (core chain, 005, 007, 008/009, 010).
- Phase 2: up to 4 concurrent (011→012 lane, 013, 014, 015).
- Phase 3: up to 4 concurrent (016, 017, 018, 019→then 023).
- Phase 5: 3 concurrent (020, 021, 022).

---

## File ownership (strictly disjoint at any concurrent moment)

### Shared-file serialization WITHIN this feature (READ THIS)
Every listed chain is strictly sequential via explicit dependency edges, so no two subtasks ever hold the same file at once.

| File | Editors | Serialized order (owner) |
|------|---------|--------------------------|
| `config/settings/restframework.py` | 003, 009, 011 | **003** (SIMPLE_JWT→RS256, expose `JWT_RSA_PRIVATE_KEY_OBJ`/`JWT_KID`) → **009** (`DEFAULT_THROTTLE_CLASSES`/`RATES`) → **011** (`DEFAULT_AUTHENTICATION_CLASSES`→CookieJWTAuthentication). 009 dep 003; 011 dep 009. |
| `accounts/serializers/auth/_token.py` | 004, 015, 018 | **004** (`token_class=KidRefreshToken` + `KidTokenRefreshSerializer`) → **015** (timing-oracle in `validate`) → **018** (`get_token` claims). 015 dep 004; 018 dep 015. |
| `accounts/controllers/_auth.py` | 004, 011, 019 | **004** (refresh view `serializer_class=KidTokenRefreshSerializer`) → **011** (cookie set/clear + `X-Token-Delivery`) → **019** (revoke actions + `logout_all` + refresh-reuse wiring). 011 dep 004; 019 dep 011. |
| `config/django/production.py` | 007, 014 | **007** (JWT_RSA enforcement) → **014** (`CSRF_TRUSTED_ORIGINS` + referrer reconcile). 014 dep 007. |
| `accounts/urls/_auth.py` | 006, 019 | **006** (Phase 1 — JWKS route) → **019** (Phase 3 — replace dead `include('djoser.urls')` with explicit `CustomUserViewSet.as_view({...})` bindings + `logout-all` + `auth/csrf/`). Serialized by phase (006 P1, 019 P3, never concurrent); 019 dep 006. The djoser include makes `CustomUserViewSet` overrides dead code, so explicit binding is mandatory. |

### Single-owner shared/infra files (within this feature)
| File | Owner |
|------|-------|
| `pyproject.toml` (add `cryptography`) | 001 — **cross-feature hazard, see below** |
| `config/settings/config.py` | 002 |
| `config/settings/apps_middlewares.py` | 013 — **cross-feature hazard, see below** |
| `config/settings/corsheaders.py` | 022 |
| `config/settings/spectacular.py` | 012 |
| `config/django/base.py` | 014 |
| `config/asgi.py` | 020 |
| `accounts/controllers/__init__.py` | 006 |
| `.env.prod.example`, `.env.local.example` | 007 |
| `.coveragerc` | 024 |

> **NOT owned here:** `config/settings/celery.py` (owned by rhitoric-utilities/006), `errors/catalog.py` (owned by rhitoric-notification-system/001), `config/routing.py` (owned by rhitoric-notification-system/010).

### Per-subtask owned paths (C = create, M = modify)
- **001**: C `config/jwt_keys.py`, `config/tests/test_jwt_keys.py`; M `pyproject.toml`
- **002**: M `config/settings/config.py`; C `config/tests/test_jwt_settings.py`
- **003**: M `config/settings/restframework.py`; C `config/tests/test_jwt_config.py`
- **004**: C `accounts/tokens.py`, `accounts/tests/test_tokens.py`; M `accounts/serializers/auth/_token.py` (P1 lines), `accounts/controllers/_auth.py` (P1 line)
- **005**: C `accounts/management/__init__.py`, `accounts/management/commands/__init__.py`, `accounts/management/commands/generate_jwt_keys.py`, `accounts/tests/test_generate_jwt_keys.py`
- **006**: C `accounts/controllers/_jwks.py`, `accounts/tests/controllers/test_jwks.py`; M `accounts/urls/_auth.py`, `accounts/controllers/__init__.py`
- **007**: M `config/django/production.py`, `.env.prod.example`, `.env.local.example`; C `config/tests/test_production_jwt.py`
- **008**: M `utils/throttles.py`; C `utils/tests/test_throttles_backport.py`
- **009**: M `config/settings/restframework.py`; C `config/tests/test_throttle_rates.py`
- **010**: C `utils/management/commands/flush_throttles.py`, `utils/tests/test_flush_throttles.py`
- **011**: C `accounts/authentication.py`, `accounts/tests/controllers/test_cookie_auth.py`; M `config/settings/restframework.py`, `accounts/controllers/_auth.py`
- **012**: C `config/spectacular_auth.py`, `config/tests/test_spectacular_auth.py`; M `config/settings/spectacular.py`
- **013**: C `config/middleware/security_headers.py`, `config/middleware/liveness_probe.py`, `config/tests/test_security_headers.py`, `config/tests/test_liveness_probe.py`; M `config/settings/apps_middlewares.py`
- **014**: M `config/django/production.py`, `config/django/base.py`; C `config/tests/test_enhanced_security.py`
- **015**: M `accounts/serializers/auth/_token.py`; C `accounts/tests/serializers/test_token_timing.py`
- **016**: C `accounts/services/session.py`, `accounts/tests/services/test_session.py`
- **017**: C `accounts/tasks/__init__.py`, `accounts/tasks/_example.py`, `accounts/tasks/token_tasks.py`, `accounts/tests/tasks/test_token_tasks.py`; DELETE `accounts/tasks.py` (does NOT touch `config/settings/celery.py`)
- **018**: M `accounts/serializers/auth/_token.py`; C `accounts/tests/serializers/test_token_claims.py`
- **019**: M `accounts/controllers/_auth.py`, `accounts/urls/_auth.py` (M — second owner, after 006); C `accounts/tests/controllers/test_session_revocation.py`
- **020**: C `utils/middleware/__init__.py`, `utils/middleware/jwt_websocket_auth.py`, `utils/tests/test_jwt_websocket_auth.py`; M `config/asgi.py`
- **021**: C `utils/websocket/__init__.py`, `utils/websocket/protocol.py`, `utils/tests/test_websocket_protocol.py`
- **022**: C `utils/websocket/rate_limit.py`, `utils/tests/test_ws_rate_limit.py`; M `config/settings/corsheaders.py`
- **023**: M `accounts/tests/controllers/test_auth.py`, `accounts/tests/serializers/test_auth.py`, `accounts/tests/conftest.py`, `accounts/tests/factories/_user.py`
- **024**: M `.coveragerc` (only if needed for untestable glue: `config/asgi.py`, `accounts/management/*`, `config/spectacular_auth.py`)

> Directory sharing under `config/tests/`, `utils/tests/`, `accounts/tests/**` is fine — each subtask creates ONLY its own uniquely-named `test_*.py` and MUST NOT modify existing `__init__.py` files or the four test files owned by **023**.

---

## Validation gate (Definition of Done)

Run after each phase and at the end (subtask 024):

```bash
# 1. Full suite (coverage floor 80% enforced by pytest.ini)
uv run pytest --ds=config.django.test

# 2. OpenAPI validates
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# 3. Phase 1 smoke test
uv run python -c "
from config.jwt_keys import generate_rsa_private_key, compute_kid, build_jwks
from accounts.tokens import KidAccessToken, KidRefreshToken
print('Phase 1 imports OK')
"

# 4. Phase 2 smoke test
uv run python -c "
from accounts.authentication import CookieJWTAuthentication, enforce_csrf
from config.middleware.security_headers import SecurityHeadersMiddleware
from config.middleware.liveness_probe import LivenessProbeMiddleware
print('Phase 2 imports OK')
"

# 5. Phase 3 smoke test
uv run python -c "
from accounts.services.session import revoke_all_sessions, detect_refresh_reuse
from accounts.tasks.token_tasks import flush_expired_jwt_tokens
print('Phase 3 imports OK')
"

# 6. Phase 5 smoke test
uv run python -c "
from utils.middleware.jwt_websocket_auth import JWTAuthMiddleware, jwt_auth_failed, get_accepted_subprotocol, extract_token_from_scope, get_user_from_token
from utils.websocket.protocol import handle_auth_rotate, send_ack, send_nack, check_idempotency
from utils.websocket.rate_limit import MessageRateLimiter
print('Phase 5 imports OK')
"

# 7. Production RS256 enforcement (subtask 007): boot without JWT_RSA_PRIVATE_KEY must raise ImproperlyConfigured.
```

Phase gates:
- **After P1+P4:** commands 1–3 green; `generate_jwt_keys` prints a `JWT_RSA_PRIVATE_KEY=` line; `GET /.well-known/jwks.json` (or configured path) returns RFC-7517 JWKS with `kid`; all 14 throttle scopes registered.
- **After Phase 2 & 3 (incl. 023):** command 4/5 green; login sets HttpOnly cookies (no body tokens unless `X-Token-Delivery: bearer`); CSRF enforced on cookie-auth mutations; privilege change / logout-all revokes sessions; full suite green.
- **After Phase 5:** command 6 green; WS connection authenticates via subprotocol/cookie token; example consumer still works.

> **Expected-red window:** between subtask 011 (cookie login) and subtask 023 (test reconciliation) the pre-existing auth suite will fail. This is expected. The Phase-2/Phase-3 gate is only authoritative once 023 has run.

---

## Active feature conflicts

`.claude/tasks/MASTER_PLAN.md` now lists TWO ACTIVE sibling features that split the rest of the same backport plan: **rhitoric-utilities** (Phases 6–11 + scaffold) and **rhitoric-notification-system** (Phase 12). They ran their own cross-plan analysis anticipating this feature. Net: **three genuine shared-file hazards** require the orchestrator to serialize edits across features (never run the conflicting subtasks concurrently). Merges are trivial (disjoint regions of each file) but ownership is technically shared.

| File | This feature | Sibling | Resolution |
|------|--------------|---------|------------|
| `config/settings/celery.py` | (removed) | **rhitoric-utilities/006** owns it fully (queues, routes, `kombu`, `flush-expired-jwt-tokens` beat by string name) | **RESOLVED by restructure.** Subtask 017 no longer touches celery.py; it only creates the `accounts.tasks.flush_expired_jwt_tokens` task so utilities/006's by-string beat resolves at runtime. No import coupling. |
| `pyproject.toml` | **001** adds `cryptography` | **rhitoric-utilities/006** adds `kombu` | **SERIALIZE.** Same file, disjoint dependency lines. Orchestrator must not run 001 and utilities/006 concurrently; sequence either order and rebase. Alternatively consolidate both deps into a single edit. |
| `config/settings/apps_middlewares.py` | **013** adds 2 `MIDDLEWARE` entries | **rhitoric-notification-system/001** adds `"notification_system"` to `PROJECT_APPS` | **SERIALIZE.** Same file, disjoint regions (MIDDLEWARE vs PROJECT_APPS). Do not run 013 and notif/001 concurrently; whichever runs second rebases the untouched region. |

**Clean (no conflict), verified:**
- `utils/middleware/jwt_websocket_auth.py`, `utils/websocket/protocol.py`, `utils/websocket/rate_limit.py`, `utils/throttles.py` — this feature CREATES/rewrites them (020/021/022/008); notification-system only CONSUMES them behind guarded imports and degrades gracefully when absent. No shared writes. (When Phase 5 lands, notif's guarded WS-auth path activates automatically.)
- `errors/catalog.py`, `config/routing.py` — owned by notification-system; this feature deliberately does NOT touch them (locked decisions 5 + WS wiring goes through `config/asgi.py` only).
- `config/settings/{config.py,restframework.py,spectacular.py}`, `config/django/{base,production}.py`, `.env.*.example` — referenced (not owned) by rhitoric-utilities; utilities' own note confirms its only owned shared-infra files are `config/django/test.py`, `config/settings/celery.py`, `pyproject.toml`.

**Action for the orchestrator:** treat `pyproject.toml` and `config/settings/apps_middlewares.py` as cross-feature serialization points. If all three features are executed by one orchestrator, gate those two edits behind a lock; if executed independently, land this feature's edits and have the sibling rebase (or vice-versa).

## Assumptions & notes for implementers

1. **Two settings objects.** Pydantic `MainSettings` (`from config.settings.config import settings`) exposes app config; the Django global (`from django.conf import settings`) exposes resolved runtime settings. The pydantic class has `DJANGO_DEBUG` (aliased `DEBUG`), not a bare `DEBUG`. `restframework.py` already reads the pydantic `settings`; keep that import style.
2. **`kid` is read from `settings.SIMPLE_JWT["KID"]`** (set by 003). `accounts/tokens.py` (004) reads it there; do NOT re-import key material.
3. **CookieJWTAuthentication falls back to `Authorization: Bearer` with NO CSRF** — this is why existing Bearer-based test fixtures keep working after the auth-class swap. What breaks in 023 is the login *response body* (cookies now) and the `get_token` *claims* (permissions list, no `is_superuser`).
4. **Session revocation contract:** `revoke_all_sessions()` (016) writes cache key `auth:revoked_after:{user_id}` (unix ts, 7-day TTL). The WS middleware (020) reads the SAME key. Keep the template string identical.
5. **Test DB is SQLite in-memory; Celery runs eager; caches are LocMemCache** (`config/django/test.py`). WS/cache tests must fail-open when Redis is absent — assert graceful degradation, never require live Redis. Clear `cache` between throttle tests.
6. **No new error codes** (locked decision 5). Reuse `AUTH__TOKEN_INVALID`, `AUTH__UNAUTHENTICATED`, `PERMISSION__DENIED`, `RATE_LIMIT__EXCEEDED`.
7. **Strip Rhitoric specifics** in every port: deleted-user/`days_remaining` branch (`_token.py`), `admin_api.` permission prefix logic, hardcoded `"rhitoric-core"` service name, hardcoded `noreply@rhitoric.com`.
