# Next.js integration blueprint

Everything a frontend engineer needs to scaffold a Next.js app against this backend
without reading the Django code. Companion to [`API_CONTRACT.md`](../API_CONTRACT.md)
(envelope/error detail) and [`AUTH.md`](../AUTH.md) (JWT/cookie mechanics) — this doc is
the frontend-shaped summary plus concrete implementation guidance. No Next.js app exists
in this repo yet; this is the spec to build one against.

---

## 1. Running the backend locally

```bash
docker compose up --build -d
```

- API base: `http://127.0.0.1:8000/api/v1/`
- Swagger: `http://127.0.0.1:8000/api/schema/docs/` (dev only, `DEBUG=True`)
- ReDoc: `http://127.0.0.1:8000/api/schema/redoc/` (dev only)
- OpenAPI JSON: `http://127.0.0.1:8000/api/schema/` — point an OpenAPI codegen tool
  (`openapi-typescript`, `orval`) at this for typed clients.

If the default ports (5432/6379/6432) collide with something else already running on the
host, override `POSTGRES_PORT` / `REDIS_PORT` / `PGBOUNCER_PORT` — see repo `README.md`.

## 2. Response envelope — every response has this shape

```ts
// Success
type ApiSuccess<T> = { success: true; data: T; meta: { request_id: string; version: "v1" } }

// Single error
type ApiError = { success: false; error: { code: string; details?: Record<string, unknown> }; meta: { request_id: string; version: "v1" } }

// Validation — multiple field errors (always HTTP 422)
type ApiValidationErrors = { success: false; errors: { code: string; details?: { field?: string } }[]; meta: { request_id: string; version: "v1" } }
```

**There is no `message` field anywhere.** The frontend owns all user-facing copy — map
`error.code` (or each `errors[].code`) to a translated string in the frontend's own i18n
layer. Never render `error.code` directly to a user.

A thin API client should discriminate on `success` and throw a typed error the UI layer
catches, e.g.:

```ts
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include", ...init })
  const body = await res.json()
  if (!body.success) throw new ApiClientError(body.error ?? { code: body.errors?.[0]?.code }, res.status)
  return body.data
}
```

`credentials: "include"` is required — auth is cookie-based (see §4).

## 3. Error codes you must handle

Full catalog in `API_CONTRACT.md`. The ones a login/account UI will hit directly:

| Code | HTTP | When |
|---|---|---|
| `AUTH__INVALID_CREDENTIALS` | 401 | Wrong password / unknown username on login |
| `AUTH__UNAUTHENTICATED` | 401 | No/expired session, protected route hit without auth |
| `AUTH__TOKEN_INVALID` | 401 | Bad/expired/revoked JWT (HTTP and WebSocket) |
| `PERMISSION__DENIED` | 403 | CSRF failure on a cookie-authenticated mutation, or real authz denial |
| `VALIDATION__MISSING_FIELD` / `VALIDATION__INVALID_FORMAT` / `VALIDATION__INVALID_VALUE` | 422 | Form validation — `details.field` names the bad field |
| `RESOURCE__NOT_FOUND` | 404 | |
| `RESOURCE__ALREADY_EXISTS` | 409 | e.g. duplicate email/username on registration |
| `RATE_LIMIT__EXCEEDED` | 429 | `details.retry_after` in seconds |
| `INTERNAL__ERROR` | 500 | Generic — show a fallback error state |

## 4. Auth flow

**Login is username-based, not email-based** — `USERNAME_FIELD` on the User model is
`username`. Design the login form around `username` + `password`; email is a separate,
independently-changeable field used for verification/reset, not login.

### Cookie mode (recommended default for a same-site or trusted-CORS Next.js app)

1. `GET /api/v1/auth/csrf/` once on app boot — sets the `csrftoken` cookie. Read it into
   JS via `document.cookie` so it can be echoed as `X-CSRFToken` on mutating requests.
2. `POST /api/v1/auth/jwt/create/` with `{username, password}` — sets HttpOnly
   `access_token` + `refresh_token` cookies automatically. Response body only contains
   `{user: {...}}`, no tokens (they're HttpOnly, JS can't and shouldn't read them).
3. Every subsequent request: `fetch(url, {credentials: "include"})`. For mutating
   requests (POST/PUT/PATCH/DELETE), also send `X-CSRFToken: <value from csrftoken cookie>`.
4. On a `401 AUTH__TOKEN_INVALID` / expired access token: `POST /api/v1/auth/jwt/refresh/`
   with no body (refresh token comes from the cookie) — also needs the CSRF header since
   it's cookie-sourced. On success, cookies are reissued; retry the original request once.
5. `POST /api/v1/auth/jwt/destroy/` to log out (needs auth) — clears both cookies and
   blacklists the refresh token. `POST /api/v1/auth/users/logout-all/` revokes every
   session (all devices).

### Bearer mode (cross-domain SPA, mobile, or if you don't want cookie/CSRF plumbing)

Send `X-Token-Delivery: bearer` on the login request — the response body then includes
`access`/`refresh` directly and **no cookies are set**. Store them in memory (not
`localStorage`, to limit XSS blast radius) and send `Authorization: Bearer <access>` on
every request. No CSRF handling needed in this mode. Refresh by posting the refresh token
in the body to `/api/v1/auth/jwt/refresh/`.

**Pick one mode per app** — mixing cookie and bearer transport in the same client adds
complexity for no benefit.

### Registration / verification / password reset

| Step | Endpoint | Notes |
|---|---|---|
| Register | `POST /api/v1/auth/users/` — `{username, email, password}` | Activation email is **disabled by default** (`SEND_ACTIVATION_EMAIL=False`) — new users are usable immediately. If a project turns this on, the activation link points straight at the **backend** (`/api/v1/auth/users/activation/{uid}/{token}/`), not a frontend route — no frontend page needed for activation. |
| Get current user | `GET /api/v1/auth/users/me/` | |
| Update profile | `PATCH /api/v1/auth/users/me/` — `{username?, email?}` | Changing `email` server-side resets `is_verified` to `false`. |
| Change password | `POST /api/v1/auth/users/set_password/` — `{current_password, new_password}` | Revokes all *other* sessions. |
| Request password reset | `POST /api/v1/auth/users/reset_password/` — `{email}` | Always 204, even for unknown emails (no enumeration). |
| Confirm password reset | `POST /api/v1/auth/users/reset_password_confirm/` — `{uid, token, new_password}` | **The email link points at a frontend route** — implement `/reset-password/[uid]/[token]` in Next.js, extract `uid`/`token` from the URL and POST them here. |
| Delete account | `DELETE /api/v1/auth/users/me/` — `{current_password}` | |

**Known backend gotcha (flag to backend owner, don't work around silently in the
frontend):** `.env.local` sets `EMAIL_FRONTEND_DOMAIN`, but `config/settings/djoser.py`
actually reads a *different*, currently-unset env var (`FRONTEND_DOMAIN`) to build the
domain in password-reset emails. Until that's fixed backend-side, reset emails will link
to Django's default Sites-framework domain, not your Next.js app. Confirm the reset-email
domain matches your frontend before shipping password reset.

## 5. Full endpoint reference

All under `/api/v1/` unless noted. Auth column: 🔓 = `AllowAny`, 🔐 = `IsAuthenticated`, 👮 = admin-only.

| Method | Path | Auth | Body → Response |
|---|---|---|---|
| POST | `auth/jwt/create/` | 🔓 | `{username,password}` → `{user}` (+cookies) |
| POST | `auth/jwt/refresh/` | 🔓 | `{refresh?}` → `{access,refresh?}` |
| POST | `auth/jwt/verify/` | 🔓 | `{token}` → `{}` |
| POST | `auth/jwt/destroy/` | 🔐 | `{refresh?}` → 204 |
| POST | `auth/users/` | 🔓 | `{username,email,password}` → user (201) |
| GET | `auth/users/` | 👮 | → user[] |
| GET/PUT/PATCH | `auth/users/{id}/` | 🔐 | → user |
| DELETE | `auth/users/{id}/` | 🔐 | `{current_password}` → 204 |
| GET/PUT/PATCH | `auth/users/me/` | 🔐 | → user (no `is_staff`) |
| DELETE | `auth/users/me/` | 🔐 | `{current_password}` → 204 |
| POST | `auth/users/set_password/` | 🔐 | `{current_password,new_password}` → 204 |
| POST | `auth/users/set_username/` | 🔐 | `{username,current_password}` → 204 |
| POST | `auth/users/reset_password/` | 🔓 | `{email}` → 204 |
| POST | `auth/users/reset_password_confirm/` | 🔓 | `{uid,token,new_password}` → 204 |
| POST | `auth/users/reset_username/` | 🔓 | `{email}` → 204 |
| POST | `auth/users/reset_username_confirm/` | 🔓 | `{uid,token,username}` → 204 |
| POST | `auth/users/logout-all/` | 🔐 | → 204 |
| GET | `auth/csrf/` | 🔓 | → `{detail}` (+ csrftoken cookie) |
| GET | `.well-known/jwks.json` | 🔓 | → JWKS (raw, not enveloped) |
| GET | `/health/`, `/ready/` | 🔓 | raw, not enveloped, not under `/api/v1/` |

`notifications` is backend-internal only (Celery + email) — no HTTP surface to integrate
against.

## 6. User object shape

```ts
type User = {
  id: number
  username: string     // the login field
  email: string
  is_active: boolean
  is_verified: boolean
  date_joined: string   // ISO 8601
  last_login: string | null
  updated_at: string
  is_staff?: boolean    // present on admin list/detail, absent on /me/
}
```

No avatar, phone, or profile fields exist on the User model in this template — it's
auth-only by design. If the product needs a profile, that's a new `Profile` model in a
separate app (O2O to `User`), not an extension of `accounts`.

## 7. Pagination

List endpoints that opt into it return:

```ts
type Paginated<T> = { data: T[]; meta: { pagination?: { page: number; page_size: number; has_next: boolean; has_previous: boolean } } }
```

No `?page` param → up to 100 rows, no pagination metadata. Pass `?page=1&page_size=20`
(page_size clamped 1–100) to paginate. There is no total count (`has_next` only) — don't
build page-number UI that requires a total; use "load more" / prev-next instead.

## 8. CORS — what to configure before pointing a Next.js dev server at this backend

Current allowed origins (`config/settings/corsheaders.py`, hardcoded, not env-driven):
`http://localhost:8080` and `http://127.0.0.1:{WEB_PORT}` (i.e. `:8000`). **Next.js's
default dev port (3000) is not in this list yet** — add `http://localhost:3000` to
`CORS_ALLOWED_ORIGINS` in `config/settings/corsheaders.py` before frontend work starts,
or the browser will block every cross-origin request. `CORS_ALLOW_CREDENTIALS = True` is
already set (required for cookie-mode auth). In production, loopback origins are
auto-stripped when `DJANGO_DEBUG=False` — the real deployed frontend origin must be added
to that same list (not env-configurable today).

## 9. WebSocket integration (optional — only one demo route exists today)

Only `ws://<host>/ws/test/` is wired, to a demo `ExampleConsumer` — treat it as a
reference pattern, not a production feature; a real feature needs its own consumer.

**Auth**: pass the JWT as a WebSocket subprotocol, not a header (browsers don't allow
custom WS headers):

```js
const ws = new WebSocket("ws://127.0.0.1:8000/ws/test/", ["access_token", jwtAccessToken])
```

The server echoes `access_token` back as the accepted subprotocol. On invalid/expired
token the connection should close with code `4401` (catalog `AUTH__TOKEN_INVALID`) — note
the current demo consumer doesn't enforce this yet, don't copy that gap into a real
consumer. No token at all falls back to session-cookie auth.

Message envelope convention for any consumer built on `utils/websocket/protocol.py`:

```ts
type Ack = { type: "ack"; message_id: string; data?: unknown }
type Nack = { type: "nack"; message_id: string; code: string; detail: string }
```

Client messages should include a unique `message_id` (string, `^[a-zA-Z0-9\-]{1,128}$`)
for idempotency (5-minute dedup window). Server-side rate limit is 15 messages/sec per
connection — a chat-like UI should debounce/throttle sends client-side to stay under that.

## 10. Suggested Next.js project shape

- **App Router**, server components for initial data fetch where the request can carry
  the `access_token` cookie automatically (same-origin or configured CORS + credentials).
- **A single typed API client module** wrapping `fetch`, implementing the envelope
  discrimination in §2, the CSRF header injection in §4, and a one-shot refresh-and-retry
  on `AUTH__TOKEN_INVALID`.
- **`middleware.ts`** for route protection — check for the presence of the (readable,
  non-HttpOnly) marker or make a lightweight `GET /api/v1/auth/users/me/` call; the actual
  `access_token` cookie is HttpOnly and invisible to `middleware.ts`/client JS by design.
- **Generate types from `/api/schema/`** (`openapi-typescript` or similar) instead of
  hand-maintaining the `User`/envelope types above — this doc's shapes are a snapshot, the
  OpenAPI schema is the live source of truth.
- **`.env.local` for the frontend**: `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1`.

## 11. Open items for the backend owner (not frontend-side fixable)

1. `EMAIL_FRONTEND_DOMAIN` vs `FRONTEND_DOMAIN` mismatch in `config/settings/djoser.py`
   (§4) — reset-email links won't point at the Next.js app until fixed.
2. `CORS_ALLOWED_ORIGINS` doesn't include the Next.js dev port and isn't env-driven for
   production origins (§8) — needs a code change per deployed frontend origin today.
3. Named throttle scopes (`auth_login`, `auth_register`, `auth_reset`, etc.) are defined
   in settings but not wired to any view — only the blanket `default_anon`/`default_user`
   rates apply today. Not a frontend blocker, just don't assume the stricter documented
   rates are actually enforced yet.
