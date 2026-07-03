# 005 — generate_jwt_keys management command (1.5)

**Status:** [PENDING]
**Phase:** 1
**Group:** cmd
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 001 (uses `config.jwt_keys`)

## Goal
Add `python manage.py generate_jwt_keys` that generates a 2048-bit RSA key and prints the base64 `JWT_RSA_PRIVATE_KEY=` line for `.env`.

## Context
`accounts/management/` does NOT exist yet — create the package. Operators run this once per environment to mint the signing key.

## Existing pattern to follow
`SRC:accounts/management/commands/generate_jwt_keys.py`. For Django command structure, mirror any existing command under `utils/management/commands/` (e.g. `starttemplateapp.py`).

## Files Owned
- `accounts/management/__init__.py` (C)
- `accounts/management/commands/__init__.py` (C)
- `accounts/management/commands/generate_jwt_keys.py` (C)
- `accounts/tests/test_generate_jwt_keys.py` (C)

## Implementation Steps

### Step 1 — the command
`class Command(BaseCommand)` with `help` text. In `handle()`:
```python
from config.jwt_keys import generate_rsa_private_key, private_key_to_pem, compute_kid
import base64
key = generate_rsa_private_key()
pem = private_key_to_pem(key)
b64 = base64.b64encode(pem.encode()).decode()
self.stdout.write(self.style.SUCCESS(f"Generated RSA key (kid={compute_kid(key)})"))
self.stdout.write("Add this to your .env file:")
self.stdout.write(f"JWT_RSA_PRIVATE_KEY={b64}")
```

## Tests (`accounts/tests/test_generate_jwt_keys.py`)
- `call_command("generate_jwt_keys", stdout=buf)`; assert output contains `JWT_RSA_PRIVATE_KEY=` and that the base64 value round-trips through `load_rsa_private_key` to a valid key.

## Validation
```bash
uv run pytest accounts/tests/test_generate_jwt_keys.py -x -v --ds=config.django.test
uv run python manage.py generate_jwt_keys --settings=config.django.test
```

## Acceptance Criteria
- [ ] `accounts/management/commands/` package created with both `__init__.py` files.
- [ ] Command prints a loadable base64 key line. Tests pass.
