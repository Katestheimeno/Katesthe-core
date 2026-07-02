# API contract validation audit (parallel, per-app)

---

## Shared orchestration

This prompt follows the **agent orchestration protocol** (`.claude/rules/workflow.md`):
1. **Clarification gate** — after reading the codebase and understanding scope, ask the user if anything is ambiguous (e.g., which contract surfaces to prioritize, whether to include WebSocket consumers, scope to specific apps). If clear, proceed immediately.
2. **Parallel execution** — Phase 1 agents launch simultaneously. Independent work never waits.
3. **Confirmation gate** — after Phase 3 consolidation, present the summary and ask the user for confirmation before generating an implementation plan for remaining fixes.
4. **Plan generation** — on confirmation, create `.claude/tasks/<feature>/MASTER_TASKS.md` with parallel groups and subtask files for schema fixes, doc corrections, and error catalog alignment.
5. **Parallel implementation + cross-review** — subtasks that don't share files get their own agent. When an agent finishes, a fresh review agent checks its work.

---

## Purpose

Run a **parallel, multi-agent validation** that checks every HTTP endpoint and WebSocket consumer against **three sources of contract truth**: the source code (authoritative), the OpenAPI schema (`@extend_schema` annotations + drf-spectacular output), and the frontend-facing documentation (`docs/front/`, plus top-level frontend guides). Drift in **any direction** is flagged: docs that don't match code, schema that doesn't match code, or docs that don't match schema.

This audit does **not** fix source code — it fixes documentation and schema annotations to match actual behavior, and reports code-level bugs separately.

---

## Hard constraints (non-negotiable)

1. **Source code is truth** for what the API actually does. Schema and docs must conform to code, not the other way around.
2. **No behavioral code changes.** Fix `@extend_schema` annotations (they're metadata, not behavior) and documentation only. Code bugs are **reported**, never patched.
3. **Error codes must match the catalog.** If `docs/error.md` or `errors/catalog.py` (if present) defines the error vocabulary, validate that controllers use registered codes and docs reference real codes.
4. **Additive-only check.** Flag any documentation or schema that implies a published field was removed, renamed, or had its type changed within the current major API version.
5. **WebSocket contracts are included.** Consumers in `*/consumers.py` have message shapes and event sequences — these are API contracts just like REST endpoints.

---

## User prompt for Claude Code (copy from here)

```markdown
You are orchestrating a **parallel API contract validation audit** of this Django repository.

**Principle:** Source code defines actual behavior. OpenAPI schema and frontend docs must match it exactly. Drift in any direction is a defect.

### Phase 0 — Discover apps, endpoints, and contract surfaces (orchestrator only)
1. Open Django settings → list **project-owned apps**.
2. Read `config/urls.py` to understand the top-level URL routing and which apps expose HTTP endpoints.
3. Identify WebSocket routing from `config/routing.py` (or equivalent ASGI routing).
4. Map each app to its contract surfaces:
   - **REST endpoints**: `<app>/controllers/` or `<app>/views.py`, `<app>/urls/`
   - **Serializers**: `<app>/serializers/` — define request/response shapes
   - **Schema annotations**: `@extend_schema` in controllers and URL files
   - **WebSocket consumers**: `<app>/consumers.py`
   - **Permissions**: `<app>/permissions/` — affect who can call what
   - **Frontend docs**: files in `docs/front/` and top-level guides relevant to this app
   - **Core API docs**: `docs/API_ENDPOINTS_PLAN.md`, `docs/EXTERNAL_API_DOC.md`, `docs/EXTERNAL_API_SPECIFICATION.md`, app-specific docs
   - **Error catalog**: `docs/error.md`, any `errors/` package
5. Assign apps that have **no HTTP endpoints** (pure internal logic) to a lightweight "contract-free" check — they only verify that other apps' docs don't falsely attribute endpoints to them.
6. Output the mapping: `{ app_label: { endpoints: [...], consumers: [...], docs: [...], schema_files: [...] } }`.

### Phase 1 — Spawn parallel contract-validation agents (one per app with endpoints)
For **each** app with REST or WebSocket endpoints, spawn **one subagent** in parallel.

**Step 1 — Extract the actual contract from source code**

For every endpoint in this app, record:
```
Endpoint ID: <METHOD> <path>
  Path:           /api/v1/...
  Methods:        GET, POST, etc.
  Permission:     [IsAuthenticated, IsOwner, ...]
  Throttle:       [class or None]
  Auth:           JWT / Session / None
  Request body:   { field: type (required/optional) } from input serializer
  Response 2xx:   { field: type } from output serializer — include envelope shape if used
  Response 4xx:   { status: code, error_code: "DOMAIN__ERROR" } from exception handling
  Query params:   from FilterSet / manual parsing
  Pagination:     cursor / page-number / none
  URL name:       django URL name
```

For every WebSocket consumer:
```
Consumer: <path>
  Auth:           how connection is authenticated
  Inbound msgs:   { type: "...", payload: {...} }
  Outbound msgs:  { type: "...", payload: {...} }
  Event sequence: connection → auth → subscribe → events → disconnect
  Groups:         channel layer group names/patterns
```

**Step 2 — Validate OpenAPI schema annotations against source code**

For each endpoint, check its `@extend_schema` (if present):
- Does `request` match the actual input serializer?
- Does `responses` match the actual output serializer + status codes?
- Are `tags` consistent with the app's domain?
- Are `parameters` (query params) correctly declared?
- Are `examples` (if any) valid instances of the declared schema?
- Is `operation_id` unique and descriptive?
- **Missing `@extend_schema`**: flag endpoints that lack schema annotations but should have them (non-trivial request/response shapes, custom status codes, or permission requirements).

**Step 3 — Validate frontend docs against source code**

For each relevant doc in `docs/front/` and top-level frontend guides:
- Every documented endpoint must exist with the documented method, path, and auth requirements
- Request body examples must match actual serializer fields (names, types, required vs optional)
- Response examples must match actual serializer output (field names, types, nesting)
- Error codes in docs must be real codes returned by the endpoint
- HTTP status codes must match actual behavior
- WebSocket message shapes and event sequences must match consumer implementation
- Auth flows must match actual permission + authentication classes
- Documented query parameters must match actual FilterSet fields or manual param parsing
- Pagination behavior must match actual viewset configuration
- Any "deprecated" labels must correspond to actual deprecation in code

**Step 4 — Validate core API docs against source code**

For `docs/API_ENDPOINTS_PLAN.md`, `docs/EXTERNAL_API_DOC.md`, `docs/EXTERNAL_API_SPECIFICATION.md`, and app-specific docs:
- Endpoint lists must match actual URL patterns
- Request/response shapes must match actual serializers
- Permissions described must match actual `permission_classes`
- Error catalogs must match actual exceptions raised

**Step 5 — Check error code consistency**

- Error codes used in controllers must follow `UPPER_SNAKE__CASE` with `DOMAIN__ERROR_NAME` format
- Error codes in documentation must exist in the actual code
- Error codes in code should be documented somewhere
- If `docs/error.md` or an error catalog exists, cross-reference it against actual usage

**Step 6 — Fix drift (docs and schema only)**

- **Fix `@extend_schema`** annotations to match actual behavior (add missing ones, correct wrong ones)
- **Fix frontend docs** to match actual endpoint contracts
- **Fix core API docs** to match actual endpoints
- **Do NOT change** controller logic, serializer fields, permissions, or any behavioral code

**Deliverable (per app)**
```
## App: <name>

### Contract inventory
| Endpoint | Method | Path | Schema? | Front doc? | Core doc? |
|----------|--------|------|---------|------------|-----------|
| ... | GET | /api/v1/... | ✅/❌/⚠️ | ✅/❌/⚠️/N/A | ✅/❌/⚠️ |

### Schema drift found and fixed
| Endpoint | Issue | Fix applied |
|----------|-------|-------------|
| ... | @extend_schema missing response 404 | Added 404 response with error schema |

### Frontend doc drift found and fixed
| Doc file | Endpoint | Issue | Fix applied |
|----------|----------|-------|-------------|
| docs/front/... | POST /api/v1/... | Request body shows `name` but serializer expects `title` | Updated field name |

### Core doc drift found and fixed
| Doc file | Issue | Fix applied |
|----------|-------|-------------|
| docs/API_ENDPOINTS_PLAN.md | Lists DELETE /api/v1/foo/ but endpoint doesn't exist | Removed from doc |

### Error code issues
| Location | Issue |
|----------|-------|
| code: path:line | Uses "INVALID_INPUT" instead of "VALIDATION__INVALID_INPUT" |
| doc: docs/front/... | References "USER__NOT_FOUND" but endpoint raises "ACCOUNT__NOT_FOUND" |

### Undocumented endpoints (exist in code, no docs)
| Method | Path | Permissions | Suggested doc location |
|--------|------|-------------|----------------------|
| ... | ... | ... | docs/front/... |

### Stale documented endpoints (in docs, not in code)
| Doc file | Endpoint claimed | Status |
|----------|-----------------|--------|
| ... | DELETE /api/v1/... | Endpoint does not exist — removed from docs |

### Code bugs found (not fixed)
| Location | Description | Severity |
|----------|-------------|----------|
| path:line | ... | Critical/High/Medium/Low |
```

### Phase 2 — Verification loop
After all Phase 1 agents complete:

1. **Orchestrator** handles cross-app contract issues:
   - Shared docs (`docs/API_ENDPOINTS_PLAN.md`, `docs/EXTERNAL_API_DOC.md`, `docs/README.md`) that reference multiple apps
   - Error catalog consistency across apps
   - Duplicate endpoint paths across apps (routing collision check)

2. **Run `uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test`** to verify the full OpenAPI schema is valid after all annotation changes.

3. For **each app that had schema or doc changes**, spawn a **verification agent** in parallel:
   - Re-read source code fresh
   - Re-read updated schema annotations and docs
   - Verify every claim matches the code
   - If aligned: report `✅ VALID`
   - If drift remains: fix and report what changed

4. If any verifier made fixes, run another round (same app only).

5. **Safety cap:** 3 rounds per app. Unresolved drift reported as `⚠️ UNRESOLVED`.

6. **Re-run schema validation** after each round that changes `@extend_schema` annotations.

### Phase 3 — Final consolidated report
```
# API Contract Validation — Final Report

## Schema validation
- `spectacular --validate --fail-on-warn`: ✅ PASS / ❌ FAIL (details)

## Per-app contract status
| App | REST endpoints | WS consumers | Schema status | Front docs | Core docs | Rounds |
|-----|---------------|-------------|---------------|------------|-----------|--------|
| game | 14 | 1 | ✅ | ✅ | ⚠️ 2 gaps | 1 |
| accounts | 8 | 0 | ✅ | ✅ | ✅ | 2 |

## All drift fixed (summary)
| Category | Count | Files touched |
|----------|------:|---------------|
| Schema annotations | ... | ... |
| Frontend docs | ... | ... |
| Core API docs | ... | ... |
| Error code fixes | ... | ... |

## Undocumented endpoints (need new frontend docs)
| App | Method | Path | Permissions |
|-----|--------|------|-------------|
| ... | ... | ... | ... |

## Stale documentation removed
| Doc file | What was removed | Reason |
|----------|-----------------|--------|
| ... | ... | Endpoint no longer exists |

## Error code audit
| Status | Count |
|--------|------:|
| Consistent (code + docs agree) | ... |
| Code-only (undocumented) | ... |
| Docs-only (stale reference) | ... |
| Format violations | ... |

## Code bugs found across all apps
| App | Location | Description | Severity |
|-----|----------|-------------|----------|
| ... | ... | ... | ... |

## Recommendations
- <missing doc files, error catalog gaps, schema coverage improvements>
```

### Phase 4 — Confirmation + plan generation (workflow protocol §3–§4)
After presenting the Phase 3 report:
1. **Ask the user for confirmation** — do they want to proceed with fixing remaining schema gaps, creating missing docs, aligning error catalogs, or addressing code bugs?
2. On confirmation, create `.claude/tasks/<contract_remediation>/MASTER_TASKS.md`:
   - Group independent fixes into **parallel groups** (different apps/files = different agents).
   - Create subtask files with scope, steps, and validation (including `spectacular --validate`).
   - Update `MASTER_PLAN.md`.
3. **Execute with parallel agents + cross-review** (workflow protocol §5–§6): implementation agents fix schema/docs, review agents verify accuracy against source code and run schema validation.

### Execution notes
- Maximize **parallelism**: all Phase 1 agents launch together; all Phase 2 verifiers launch together per round.
- Verification agents **always re-read source code fresh** — never inherit prior agent's model.
- When fixing `@extend_schema`, ensure the annotation reflects **actual** behavior, not aspirational behavior.
- If an endpoint lacks a serializer (raw `Response({...})`), the schema annotation is the **only** contract definition — flag these for serializer extraction but don't block the audit.
- For WebSocket consumers, there is no OpenAPI equivalent — the contract lives in frontend docs only, so doc accuracy is critical.
- Use `docs/error.md` as the error vocabulary reference where it exists; otherwise derive from code.
- The `spectacular --validate` check after schema changes is **mandatory** — if it fails, the annotation fix is wrong.

Begin with Phase 0, then Phase 1 in parallel, then Phase 2 verification loop (with schema validation), then Phase 3, then Phase 4 (on confirmation).
```

---

## Optional tweaks (edit before paste)

- **Read-only mode (report only):** Append: `"All subagents produce reports only — zero file edits. Output drift findings for human review before changes."`
- **Single app focus:** Replace Phase 0 with: `"Validate only the <app_name> app's API contracts."`
- **Schema only (skip docs):** Add: `"Only validate and fix @extend_schema annotations. Skip documentation checks."`
- **Docs only (skip schema):** Add: `"Only validate and fix documentation. Skip @extend_schema checks."`
- **Frontend docs only:** Add: `"Only validate docs/front/ and top-level frontend guides. Skip core API docs and schema."`
- **Include response testing:** Append: `"After fixing docs, generate curl/httpie examples for each endpoint and verify they produce responses matching the documented shape. Requires a running dev server."`

---

## Related project files

- URL routing: `config/urls.py`
- WebSocket routing: `config/routing.py`
- OpenAPI config: `config/settings/spectacular.py`, `config/spectacular_pydantic.py`
- Error reference: `docs/error.md`
- API plan: `docs/API_ENDPOINTS_PLAN.md`
- External API docs: `docs/EXTERNAL_API_DOC.md`, `docs/EXTERNAL_API_SPECIFICATION.md`
- Frontend docs: `docs/front/`
- Frontend game flow: `docs/GAME_FRONTEND_ENDPOINTS_AND_FLOW.md`
- Schema validation skill: `.claude/skills/openapi-validate-skill.md`
- Code audit prompt: `.claude/prompts/parallel-django-app-audit.md`
- Docs alignment prompt: `.claude/prompts/docs-alignment-audit.md`
