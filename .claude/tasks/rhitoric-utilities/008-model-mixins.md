# 008 — Enhanced SoftDelete + BooleanChoices mixins (11.1 + 11.2)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** none

## Goal
Upgrade `SoftDeleteModel` to a full queryset/manager pattern with dual managers and `hard_delete()`, and add a `BooleanChoices` base class — updating `utils/models/__init__.py` re-exports for both.

## Context
This subtask **owns `utils/models/__init__.py` entirely** (bundling 11.1 + 11.2) to keep file ownership disjoint: 11.1 already re-exports via `from ._softdelete import *`, and 11.2 needs to add `from .choices import *`. The current `_softdelete.py` is minimal (`is_deleted` + `delete()` only). **Existing `SoftDeleteModel` tests in `utils/tests/test_models.py` (class `TestSoftDeleteModel`, ~lines 162-277) MUST still pass** — the default `objects` manager stays unfiltered (returns all rows).

## Key design decision (do NOT re-litigate)
- `objects = models.Manager()` — default, returns ALL rows (admin-safe, migration-safe, no surprise missing rows).
- `alive_objects = SoftDeleteManager()` — explicit opt-in to `is_deleted=False` filtering.

## Existing pattern to follow
- `SRC:.../utils/models/_softdelete.py` — copy the upgraded `SoftDeleteQuerySet` / `SoftDeleteManager` / `SoftDeleteModel`.
- `SRC:.../utils/models/choices.py` — copy the `BooleanChoices` base class.
- Sibling mixins: `utils/models/_timestamp.py`, `utils/models/_status.py` for the `imports`/`__all__` re-export convention.

## ⚠ Blast-radius note (read before editing `_softdelete.py`)
`SoftDeleteModel` is a base of `utils/models/_audit.py::AuditModel` (`class AuditModel(TimeStampedModel, TrackableModel, SoftDeleteModel)`). Adding `alive_objects` and changing `delete()`'s return signature propagates to `AuditModel` and every concrete descendant. This is expected and low-risk: both managers set `use_in_migrations = False` (no migration), and `objects` is declared FIRST so it stays `_default_manager` (admin/relations unaffected). Before finishing, run `grep -rn "AuditModel)" --include=*.py` (and for `SoftDeleteModel)`) to list concrete subclasses and confirm none relies on the old `.delete()` returning `None` or defines its own conflicting `alive_objects`/`objects`. If one does, flag it — do not silently override.

## Files Owned
- `utils/models/_softdelete.py`
- `utils/models/choices.py`
- `utils/models/__init__.py`
- `utils/tests/test_softdelete.py`
- `utils/tests/test_choices.py`

## Implementation Steps

### Step 1 — Upgrade `utils/models/_softdelete.py`
Replace with (from SRC):
- `SoftDeleteQuerySet(models.QuerySet)` with `.alive()` (`filter(is_deleted=False)`), `.dead()` (`filter(is_deleted=True)`), `.delete()` (bulk `self.update(is_deleted=True)`, returns `(count, {label: count})`), `.hard_delete()` (`super().delete()`).
- `SoftDeleteManager(models.Manager)` with `get_queryset()` returning `SoftDeleteQuerySet(self.model, using=self._db).alive()`.
- `SoftDeleteModel(models.Model)` (abstract) with `is_deleted`, `objects = models.Manager()`, `alive_objects = SoftDeleteManager()`, `delete(self, using=None, keep_parents=False)` doing `self.is_deleted = True; self.save(update_fields=["is_deleted"]); return (1, {self._meta.label: 1})`, and `hard_delete(self, using=None, keep_parents=False)` → `super().delete(using=using, keep_parents=keep_parents)`. Keep the Django-compatible `using`/`keep_parents` params (admin/cascade compatibility) — do not drop them.
- `__all__ = ["SoftDeleteModel", "SoftDeleteManager", "SoftDeleteQuerySet"]`.

### Step 2 — Create `utils/models/choices.py`
```python
from django.db import models

class BooleanChoices(models.Choices):
    """Base class for boolean-valued choices (True/False members)."""
    ...
```
Keep the docstring showing the `YES = True, "Yes"` usage. Add `__all__ = ["BooleanChoices"]` for clean re-export.

### Step 3 — Update `utils/models/__init__.py`
- Ensure `from ._softdelete import *` is present (it is).
- Add `from .choices import *` (place it near the other mixin imports).

## Tests

### `utils/tests/test_softdelete.py` (`@pytest.mark.django_db`)
**Test-model setup (do NOT copy `TestSoftDeleteModel`'s in-memory approach for these DB-backed cases).** The existing `utils/tests/test_models.py::TestSoftDeleteModel` deliberately declares its model with `app_label='test_app'` and never creates a table (it stubs `save()` and asserts only in-memory) — that pattern CANNOT support the manager/queryset/`hard_delete` assertions below, which require a real table. Instead, define one concrete subclass at module level and create its table in a fixture:
```python
# module level
class SoftDeleteExample(SoftDeleteModel):
    class Meta:
        app_label = "utils"          # an installed app so the model registers

@pytest.fixture
def sd_table(db):
    from django.db import connection
    with connection.schema_editor() as se:
        se.create_model(SoftDeleteExample)
    yield
    with connection.schema_editor() as se:
        se.delete_model(SoftDeleteExample)
```
Use the `sd_table` fixture for every DB-backed test below. Cover:
- `objects` returns ALL rows including soft-deleted (default unfiltered) — the invariant that keeps existing tests green.
- `alive_objects` returns only `is_deleted=False` rows.
- Instance `.delete()` sets `is_deleted=True`, persists via `update_fields`, row still present in `objects`, absent from `alive_objects`, and returns `(1, {label: 1})`.
- `.hard_delete()` actually removes the row from the DB.
- `SoftDeleteQuerySet.alive()` / `.dead()` filter correctly.
- Queryset `.delete()` bulk soft-deletes and returns `(count, {label: count})`; queryset `.hard_delete()` removes rows.

### `utils/tests/test_choices.py` (no DB)
- Define `class YesNoChoices(BooleanChoices): YES = True, "Yes"; NO = False, "No"`.
- Assert `YesNoChoices.YES.value is True`, `YesNoChoices.NO.value is False`, labels `"Yes"`/`"No"`, and `YesNoChoices.choices == [(True, "Yes"), (False, "No")]`.

## Validation
```bash
uv run pytest utils/tests/test_softdelete.py utils/tests/test_choices.py utils/tests/test_models.py -x -v --ds=config.django.test
uv run python -c "from utils.models import SoftDeleteModel, SoftDeleteManager, SoftDeleteQuerySet, BooleanChoices; print('OK')"
```

## Acceptance Criteria
- [ ] `SoftDeleteQuerySet`, `SoftDeleteManager`, `SoftDeleteModel`, `BooleanChoices` all importable from `utils.models`.
- [ ] Default `objects` unfiltered; `alive_objects` filtered.
- [ ] Instance `.delete()` uses `update_fields=["is_deleted"]` and returns Django-style `(count, {label: count})`.
- [ ] `hard_delete()` truly removes rows.
- [ ] Existing `utils/tests/test_models.py::TestSoftDeleteModel` still passes unchanged.
- [ ] `utils/models/__init__.py` re-exports both `_softdelete` and `choices`.
