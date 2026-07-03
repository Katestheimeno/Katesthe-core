# Documentation index

Katesthe-core is a Django bootstrap template. This index points to the living docs that describe what the template ships and how to use it.

## Topical docs

| Doc | Covers |
|---|---|
| [`API_CONTRACT.md`](API_CONTRACT.md) | Response envelope shape, error-code catalog, HTTP status mapping, throttling defaults, pagination usage, health/readiness endpoints |
| [`BACKEND_UTILITIES.md`](BACKEND_UTILITIES.md) | Transactional email pattern, CSV/XLSX export helpers, upload-path + transactional-outbox utilities, Celery task template, optional Sentry hook, debug-payload middleware |

## Traceability & changelog

- `docs/changes/` — one file per substantive change, dated `YYYYMMDD_HHMMSS_<slug>.md` (see `.claude/rules/docs.md` §2 for the template).
- `CHANGELOG.md` (repo root) — Keep-a-Changelog style, one entry per shipped change, links back to the matching `docs/changes/` file for anything non-trivial.

## Project rules

Architecture, layering, testing, and API conventions live in `.claude/rules/*.md` (read `.claude/CLAUDE_ENTRYPOINT.md` first). This `docs/` tree documents *what exists*; `.claude/rules/` documents *how to build more of it*.
