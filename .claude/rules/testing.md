# Testing discipline

## Migration Notes

**Source files merged (3):** `testing/00-django-testing-discipline.mdc`, `testing/03-test-structure.mdc`, `testing/04-test-commands.mdc`.

**Conflicts resolved (C5):** the three sources restated the "what to test" checklist with subtle differences. Merged into one canonical list; test structure and command cheat-sheet kept verbatim.

**Deliberately removed:** none.

Related skill: `.claude/skills/run-tests-skill.md` (concrete BTV for running the suite).

---

## 1. Mandatory triggers — tests MUST exist when you add

- New model or model method
- New service method or new branch in an existing service
- New selector
- New serializer / schema
- New view or viewset action
- New permission class
- New signal handler
- New Celery task (retry behavior + idempotency branches)
- Any new `if/else`, `try/except`, or early `return` in existing code

## 2. Structure — tests live inside each app

```
<app>/tests/
  __init__.py
  conftest.py                     # app-scoped fixtures
  factories/
    __init__.py
    user.py
  models/
    test_<name>.py
  controllers/                    # or views/
    test_<name>.py
  services/
    test_<name>.py
  selectors/
    test_<name>.py
  serializers/
    test_<name>.py
```

`pytest.ini` `testpaths` already lists every app's `tests` directory.

## 3. Coverage

- **Project floor:** 75 % (`--cov-fail-under=75` in `pytest.ini`).
- **New code aspiration:** 100 % branch coverage. Every `if/else`, `try/except`, early `return`, new conditional must have a test.
- **Coverage is behavior, not lines.** A green line with no assertion is wallpaper.

## 4. Test cases you must write for every change

| Category | What to verify |
|---|---|
| Happy path | Correct input → correct output |
| Edge cases | Empty / None / boundary values / empty queryset |
| Failure modes | Invalid input, missing fields, malformed data |
| Permissions | Unauthenticated, wrong role, correct role, **object-level (IDOR)** |
| Validation | Every `validate_*` method and custom validator |
| QuerySet behavior | Filtering, ordering, annotation, N+1 count if critical |
| Side effects | Signals fired, cache invalidated, tasks enqueued, emails sent |
| Authorization boundaries | User A cannot access user B's data |

## 5. Discipline

- **Factory Boy factories** live in `<app>/tests/factories/`. No ad-hoc `Model.objects.create(...)` in tests — write a factory.
- **Reuse fixtures** from `conftest.py`. Don't redeclare per test file.
- **Mock externals** — email, OneSignal, Ably, Mapbox, Celery `.delay()`. Integration with real services belongs to staging, not pytest.
- **`@pytest.mark.django_db`** only when the test needs the DB.
- **`freezegun`** for time-sensitive tests.
- **Parametrize** similar cases rather than copy-paste.
- **One logical assertion per test** (multiple `assert` lines OK if same concept).
- **Test names are sentences.** `test_client_cannot_accept_quote_on_intervention_they_do_not_own` > `test_accept_quote_403`.

## 6. Markers

Declared in `pytest.ini`:

- `slow` — deselect with `-m "not slow"`
- `integration` — end-to-end
- `unit` — isolated
- `auth`, `api`, `django_db`

## 7. Commands — cheat sheet

```bash
# Full suite (cov gate 75 %)
uv run pytest

# Specific file
uv run pytest game/tests/test_controllers.py

# Specific test by name
uv run pytest -k "test_reply_view_403_when_not_owner"

# Exclude slow
uv run pytest -m "not slow"

# HTML coverage report
uv run pytest --cov-report=html && xdg-open htmlcov/index.html

# Fail fast, verbose
uv run pytest -x -v
```

## 8. What **not** to do

- **Do not** mock what you own. If your service calls your selector, let the real selector run against a real DB.
- **Do not** commit tests with `@pytest.mark.skip` unless there's a ticket reference in the reason.
- **Do not** rely on test-order side effects — each test is self-contained.
- **Do not** hit external networks from unit tests.
