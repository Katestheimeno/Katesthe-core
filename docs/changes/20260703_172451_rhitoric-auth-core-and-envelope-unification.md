# Change: Rhitoric auth-core backport + response-envelope unification

**Date:** 2026-07-03 17:24
**Author:** AI-assisted
**Prompt Scope:** Backport RS256 JWT / HttpOnly-cookie auth / session revocation / throttle-class architecture / WebSocket JWT auth from Rhitoric-core (Phases 1-5 of `RHITORIC_BACKPORT_PLAN.md`), then bring every `accounts` endpoint onto the standard `{success, data|error, meta}` response envelope and `errors/catalog.py` error codes.

## Summary

Two passes landed together. The first (`/flow impl rhitoric-auth-core`) ports the generic, domain-agnostic pieces of Rhitoric-core's auth stack: RS256 JWT signing with a JWKS endpoint, HttpOnly-cookie transport with CSRF enforcement, session revocation with refresh-reuse detection, the universal throttle-class hierarchy, and JWT WebSocket authentication. The second pass audits every response in `accounts/controllers/_auth.py` and closes the gaps where success bodies (login, refresh, verify, the whole user CRUD surface) or error bodies (logout, activation) bypassed the envelope/catalog convention entirely.

## Reason for Change

Feature request (auth hardening backport) followed by a codebase-wide consistency audit that surfaced: (1) most of the `accounts` API's *success* responses were never wrapped in the envelope — only errors were, via the global exception handler; (2) two views (`CustomJWTLogoutView`, `CustomActivationView`) hand-rolled `{'detail': str}` / `{'message': str}` bodies that bypassed the catalog entirely; (3) two djoser Token-model views were dead code, unrouted since the app doesn't install `rest_framework.authtoken`.

## Files Modified

| File | Change |
|------|--------|
| `config/jwt_keys.py`, `config/tests/test_jwt_keys.py` | RSA key generation/loading, `kid` fingerprint, JWKS builder (new) |
| `config/settings/config.py` | JWT/cookie/throttle Pydantic settings fields |
| `accounts/tokens.py`, `accounts/tests/test_tokens.py` | `KidAccessToken`/`KidRefreshToken` (new) |
| `accounts/controllers/_jwks.py`, `accounts/tests/controllers/test_jwks.py` | JWKS endpoint (new) |
| `accounts/management/commands/generate_jwt_keys.py` | key-gen command (new) |
| `config/settings/restframework.py` | RS256 `SIMPLE_JWT`, throttle rates, `CookieJWTAuthentication` wiring |
| `utils/throttles.py`, `utils/management/commands/flush_throttles.py` | throttle class hierarchy + flush command |
| `config/django/production.py`, `config/django/base.py` | RS256 boot enforcement, hardened security settings |
| `config/middleware/security_headers.py`, `config/middleware/liveness_probe.py`, `config/spectacular_auth.py`, `accounts/apps.py` | security-headers/liveness middleware, OpenAPI auth scheme registration |
| `accounts/authentication.py` | `CookieJWTAuthentication` + CSRF enforcement (new) |
| `accounts/serializers/auth/_token.py` | kid refresh serializer, timing-oracle defense, `permissions` claim |
| `accounts/services/session.py`, `accounts/tasks/token_tasks.py` | session revocation + expired-token housekeeping (new) |
| `utils/middleware/jwt_websocket_auth.py`, `utils/websocket/protocol.py`, `utils/websocket/rate_limit.py`, `config/asgi.py` | WebSocket JWT auth (new) |
| `utils/consumers.py` | example consumer error frames switched to catalog codes |
| `accounts/controllers/_auth.py`, `accounts/urls/_auth.py` | cookie login/refresh/logout views, revocation wiring, **and** the envelope-unification pass: `CustomUserViewSet.finalize_response()` override; login/refresh/verify success bodies wrapped; `CustomJWTLogoutView`/`CustomActivationView` moved from hand-rolled dicts to `raise AppAPIError(...)`; dead `CustomTokenCreateView`/`CustomTokenDestroyView` deleted |

## Refactors Performed

- `accounts/tasks.py` converted to a package (`accounts/tasks/`) to hold both the existing example task and the new `flush_expired_jwt_tokens` task.
- `accounts/urls/_auth.py` replaced the dead `include('djoser.urls')` with explicit `CustomUserViewSet.as_view({...})` bindings — the include had made `CustomUserViewSet`'s method overrides unreachable.
- `CustomActivationView.post` trimmed from ~88 to ~45 lines while adding the catalog-code branches, keeping it under the 60-line function cap.

## Reused Logic

- `utils.api_response.ok`/`meta_for_request` and `errors.exceptions.AppAPIError` (pre-existing envelope/catalog infrastructure) — this change is purely about *applying* them everywhere, not building new envelope machinery.
- `utils.drf_error_envelope.coerce_drf_error_response` — unchanged; still the fallback for any DRF built-in `{"detail": ...}` response.

## Related Tests Added

| File | Covers |
|------|--------|
| `config/tests/test_jwt_keys.py`, `test_jwt_settings.py`, `test_jwt_config.py`, `test_production_jwt.py` | RSA key handling, settings, RS256 config, production enforcement |
| `accounts/tests/test_tokens.py`, `test_generate_jwt_keys.py` | kid token classes, key-gen command |
| `accounts/tests/controllers/test_jwks.py`, `test_cookie_auth.py`, `test_session_revocation.py` | JWKS shape, cookie transport + CSRF, revocation/reuse-detection flows |
| `accounts/tests/serializers/test_token_timing.py`, `test_token_claims.py` | timing defense, permissions claim |
| `accounts/tests/services/test_session.py`, `accounts/tests/tasks/test_token_tasks.py` | revocation service, housekeeping task |
| `utils/tests/test_throttles_backport.py`, `test_throttle_rates.py`, `test_flush_throttles.py` | throttle classes, rates, flush command |
| `utils/tests/test_jwt_websocket_auth.py`, `test_websocket_protocol.py`, `test_ws_rate_limit.py` | WS auth middleware, protocol helpers, rate limiter |
| `config/tests/test_security_headers.py`, `test_liveness_probe.py`, `test_spectacular_auth.py`, `test_enhanced_security.py` | middleware, OpenAPI auth docs, production security |
| `accounts/tests/controllers/test_auth.py` (updated) | envelope shape on CRUD/login/refresh/verify/logout/activation, catalog codes on every failure branch |

Full suite: 670 passed, 1 skipped, 87.5% coverage (floor 80%). `spectacular --validate --fail-on-warn` exits 0.

## Documentation Updated

- `docs/AUTH.md` — new topical doc for the auth subsystem (RS256/JWKS, cookie auth, session revocation, WS auth).
- `docs/API_CONTRACT.md` — response-envelope coverage note corrected (success responses are no longer opt-in-only for `accounts`).
- `docs/README.md` — added `AUTH.md` to the topical docs index.
- `CHANGELOG.md` — this entry.
