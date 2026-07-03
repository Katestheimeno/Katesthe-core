"""
Tests for config/jwt_keys.py.
"""

import base64

from cryptography.hazmat.primitives.asymmetric import rsa

from config.jwt_keys import (
    build_jwks,
    compute_kid,
    generate_rsa_private_key,
    load_rsa_private_key,
    load_rsa_public_key,
    private_key_to_pem,
    public_key_to_pem,
)


class TestGenerateRsaPrivateKey:
    def test_generate_rsa_private_key_returns_2048_bit_key(self):
        key = generate_rsa_private_key()

        assert isinstance(key, rsa.RSAPrivateKey)
        assert key.key_size == 2048


class TestPrivateKeyPemRoundTrip:
    def test_private_key_to_pem_round_trips_through_base64_to_equivalent_key(self):
        key = generate_rsa_private_key()

        pem = private_key_to_pem(key)
        pem_b64 = base64.b64encode(pem.encode("utf-8")).decode("ascii")
        loaded_key = load_rsa_private_key(pem_b64)

        original_numbers = key.private_numbers()
        loaded_numbers = loaded_key.private_numbers()
        assert original_numbers.public_numbers.n == loaded_numbers.public_numbers.n
        assert original_numbers.public_numbers.e == loaded_numbers.public_numbers.e
        assert original_numbers.d == loaded_numbers.d


class TestPublicKeyPemRoundTrip:
    def test_public_key_to_pem_round_trips_through_base64_to_equivalent_public_key(self):
        key = generate_rsa_private_key()

        pem = public_key_to_pem(key)
        pem_b64 = base64.b64encode(pem.encode("utf-8")).decode("ascii")
        loaded_public_key = load_rsa_public_key(pem_b64)

        assert key.public_key().public_numbers() == loaded_public_key.public_numbers()

    def test_public_key_to_pem_accepts_a_bare_public_key(self):
        key = generate_rsa_private_key()
        public_key = key.public_key()

        pem = public_key_to_pem(public_key)
        pem_b64 = base64.b64encode(pem.encode("utf-8")).decode("ascii")
        loaded_public_key = load_rsa_public_key(pem_b64)

        assert public_key.public_numbers() == loaded_public_key.public_numbers()


class TestComputeKid:
    def test_compute_kid_is_deterministic_for_the_same_key(self):
        key = generate_rsa_private_key()

        assert compute_kid(key) == compute_kid(key)

    def test_compute_kid_differs_across_distinct_keys(self):
        key_a = generate_rsa_private_key()
        key_b = generate_rsa_private_key()

        assert compute_kid(key_a) != compute_kid(key_b)

    def test_compute_kid_is_a_16_character_hex_string(self):
        key = generate_rsa_private_key()

        kid = compute_kid(key)

        assert len(kid) == 16
        assert all(c in "0123456789abcdef" for c in kid)


class TestBuildJwks:
    def test_build_jwks_contains_only_public_material(self):
        key = generate_rsa_private_key()
        kid = compute_kid(key)

        jwks = build_jwks(key, kid)

        assert list(jwks.keys()) == ["keys"]
        assert len(jwks["keys"]) == 1
        jwk = jwks["keys"][0]
        assert jwk["kty"] == "RSA"
        assert jwk["use"] == "sig"
        assert jwk["alg"] == "RS256"
        assert jwk["kid"] == kid
        assert "n" in jwk
        assert "e" in jwk
        assert "d" not in jwk
        assert "p" not in jwk
        assert "q" not in jwk

    def test_build_jwks_with_previous_key_returns_two_keys_with_distinct_kids(self):
        current_key = generate_rsa_private_key()
        current_kid = compute_kid(current_key)
        previous_key = generate_rsa_private_key()
        previous_kid = compute_kid(previous_key)

        jwks = build_jwks(
            current_key,
            current_kid,
            previous_public_key=previous_key.public_key(),
            previous_kid=previous_kid,
        )

        assert len(jwks["keys"]) == 2
        kids = [jwk["kid"] for jwk in jwks["keys"]]
        assert kids == [current_kid, previous_kid]
        assert kids[0] != kids[1]
        for jwk in jwks["keys"]:
            assert "d" not in jwk
            assert "p" not in jwk
            assert "q" not in jwk
