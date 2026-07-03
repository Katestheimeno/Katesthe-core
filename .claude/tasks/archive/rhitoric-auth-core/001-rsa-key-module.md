# 001 — RSA key management module (1.1)

**Status:** [PENDING]
**Phase:** 1
**Group:** core
**Risk:** MEDIUM
**Effort:** 30m
**Dependencies:** none

## Goal
Create `config/jwt_keys.py` with RSA key loading, `kid` computation, and JWKS building; add `cryptography` to dependencies.

## Context
RS256 JWT signing, the JWKS endpoint, `kid` token headers, and WebSocket auth all depend on this key infrastructure. It is pure crypto with no Django imports.

## Existing pattern to follow
`SRC:config/jwt_keys.py` — copy the pattern verbatim (it is fully generic). No domain logic to strip.

## Files Owned
- `config/jwt_keys.py` (C)
- `config/tests/test_jwt_keys.py` (C)
- `pyproject.toml` (M — add `cryptography`)

## Implementation Steps

### Step 1 — `config/jwt_keys.py`
Implement, using `cryptography.hazmat.primitives.asymmetric.rsa` + `serialization` + `hashes`:
- `load_rsa_private_key(pem_b64: str) -> rsa.RSAPrivateKey` — base64-decode, `serialization.load_pem_private_key(..., password=None)`.
- `load_rsa_public_key(pem_b64: str) -> rsa.RSAPublicKey` — base64-decode, `serialization.load_pem_public_key`.
- `generate_rsa_private_key() -> rsa.RSAPrivateKey` — `rsa.generate_private_key(public_exponent=65537, key_size=2048)`.
- `private_key_to_pem(key) -> str` — PKCS8 PEM, `NoEncryption()`, `.decode()`.
- `public_key_to_pem(key) -> str` — accept a private OR public key; if private, `key.public_key()`; serialize `SubjectPublicKeyInfo` PEM.
- `compute_kid_from_public(public_key) -> str` — SHA-256 of the public key DER (`SubjectPublicKeyInfo`), hex, truncated to 16 chars.
- `compute_kid(key) -> str` — derive public key from a private key, delegate to `compute_kid_from_public`.
- `build_jwks(key, kid, algorithm="RS256", previous_public_key=None, previous_kid=None) -> dict` — RFC 7517 dict `{"keys": [...]}`. Each JWK: `kty="RSA"`, `use="sig"`, `alg=algorithm`, `kid`, and base64url-encoded `n` (modulus) and `e` (public exponent) with NO padding. Include the previous key as a second entry when both `previous_public_key` and `previous_kid` are provided. **Only public material — never emit `d`, `p`, `q`.**

### Step 2 — `pyproject.toml`
Add `cryptography` to the runtime `dependencies` list (not optional — plan "What NOT to Do" #8). Run `uv lock` if the repo convention requires it.

## Tests (`config/tests/test_jwt_keys.py`)
- `generate_rsa_private_key()` returns a 2048-bit key.
- Round-trip: `private_key_to_pem` → base64 → `load_rsa_private_key` yields an equivalent key.
- `compute_kid` is deterministic (same key → same 16-char hex kid) and differs across keys.
- `build_jwks(key, kid)` returns `{"keys":[{...}]}` with `kty/use/alg/kid/n/e` and NO private fields (`d`,`p`,`q` absent).
- `build_jwks(..., previous_public_key=pub2, previous_kid=kid2)` returns two keys with distinct kids.

## Validation
```bash
uv run pytest config/tests/test_jwt_keys.py -x -v --ds=config.django.test
uv run python -c "from config.jwt_keys import generate_rsa_private_key, compute_kid; k=generate_rsa_private_key(); print(compute_kid(k))"
```

## Acceptance Criteria
- [ ] All 8 functions present with the signatures above.
- [ ] JWKS output contains only public material.
- [ ] `cryptography` declared in `pyproject.toml`.
- [ ] Tests pass; smoke command prints a 16-char kid.
