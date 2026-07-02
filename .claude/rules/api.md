# API conventions

## Migration Notes

**Source files merged (1):** `api/api-convention.mdc`.

**Conflicts resolved:** C9 (OpenAPI validation gate appears in both `docs/docs-and-schema.mdc` and `testing/04-test-commands.mdc`) — the **rule** "you MUST validate before merge" stays in `docs.md`; the **command** (`spectacular --validate --fail-on-warn`) lives in `.claude/skills/openapi-validate-skill.md`.

---

## 1. Response envelope — always

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "meta": { "request_id": "req_01HX7Z...", "version": "v1" }
}
```

**Failure (single error):**
```json
{
  "success": false,
  "error": { "code": "USER__NOT_FOUND" },
  "meta": { "request_id": "req_...", "version": "v1" }
}
```

**Failure (validation — multiple):**
```json
{
  "success": false,
  "errors": [ { "code": "VALIDATION__MISSING_FIELD", "details": { "field": "email" } } ],
  "meta": { ... }
}
```

- `meta` is always present with `request_id` and `version`.
- **No `message` field.** Frontend owns i18n — backend returns codes only.
- **Helpers:** follow existing patterns in this repo (standard envelope where implemented in `.cursor/rules/api-convention.mdc`); older endpoints may still return plain DRF/Python dicts until refactored.

## 2. Error codes — strict format

- **`UPPER_SNAKE_CASE`**, namespaced with double underscore: `DOMAIN__ERROR_NAME`.
- **Max one `__` separator** — `DOMAIN__ERROR_NAME`, never `DOMAIN__SUB__ERROR_NAME`.
- **Verb-last:** `NOT_FOUND`, `ALREADY_EXISTS`, `EXPIRED`, `FAILED`, `INVALID`, `DENIED`.
- **No redundant suffixes** — never `_ERROR`, `_FAILURE`, `_EXCEPTION`.
- **Catalog is canonical** where the project defines one (see `.cursor/rules/api-convention.mdc` and any `errors/` package). Once shipped in a major version, a code is **immutable**.
- **Raised via** the project's standard API exception type + exception handler — map to the envelope consistently (`config/` as wired in this repo).

### Authorized namespaces

Target state (from `.cursor/rules/api-convention.mdc`): `AUTH`, `USER`, `ACCOUNT`, `PAYMENT`, `MEDIA`, `COURSE`, `VALIDATION`, `PERMISSION`, `RATE_LIMIT`, `NOTIFICATION`, `INTEGRATION`, `INTERNAL`, `RESOURCE`, plus Rhitoric domains such as **`GAME`**, **`ELEARNING`**, **`REVIEW`**, **`AI_CORE`**, **`ADMIN`**, **`TICKETS`** as registered in the shared error catalog.

**Note:** Rhitoric may still expose legacy `{"error": "..."}` shapes in some older views; new or refactored endpoints should move toward machine-coded errors and the standard envelope.

New namespaces → discuss first; register before use.

## 3. HTTP status mapping

| Status | Use for |
|---|---|
| 200 | success |
| 201 | created |
| 400 | client input error (malformed body) |
| 401 | unauthenticated (missing/invalid token) |
| 403 | authenticated but not authorized |
| 404 | resource not found |
| 409 | conflict / duplicate |
| 422 | semantically invalid input (validator failure) |
| 429 | rate-limited |
| 500 | internal error |
| 502 | upstream (provider) error |
| 503 | service / provider unavailable |

## 4. URL design

- **RESTful nouns** under `/api/v1/` (Rhitoric examples — see `docs/API_ENDPOINTS_PLAN.md`): `/games/`, `/games/{game_code}/`, `/categories/`, `/topics/`, `/clubs/`, `/leaderboards/`, e-learning routes under `/api/v1/` as documented in `docs/ELEARNING_API.md`.
- **Nested under parent** when scoped: e.g. `/api/v1/games/{game_code}/voice-response/`.
- **Actions as sub-resources:** e.g. `/api/v1/games/{game_code}/join/`, `/api/v1/auth/login/`.
- **Versioning** via path prefix. Never route-version by header.

## 5. Idempotency

- **Payments, external side effects, and any duplicate-submission-prone write** accept an `Idempotency-Key` header.
- Persist `key + outcome` in the DB with TTL matching the client retry window.
- Repeated requests with the same key return the same outcome — no re-execution.

## 6. Additive-only evolution

Within a major version, you **MUST NOT**:
- Remove or rename a published response field.
- Change type or meaning of an existing field.
- Narrow an accepted enum value.
- Turn a previously-successful input into a 4xx.
- Add a **required** request field.

You **SHOULD**:
- Add optional fields instead of repurposing existing ones.
- Deprecate fields with at least a 2-version notice (mark in OpenAPI + CHANGELOG).
