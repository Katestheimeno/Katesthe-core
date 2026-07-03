"""
RSA key management for JWT RS256 signing.
Path: config/jwt_keys.py

Handles loading RSA keys from environment (base64-encoded PEM),
auto-generating transient keys for development, computing kid,
and building JWKS responses.
"""

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def load_rsa_private_key(pem_b64: str) -> rsa.RSAPrivateKey:
    """Load an RSA private key from a base64-encoded PEM string."""
    pem_bytes = base64.b64decode(pem_b64)
    return serialization.load_pem_private_key(pem_bytes, password=None)


def load_rsa_public_key(pem_b64: str) -> rsa.RSAPublicKey:
    """Load an RSA public key from a base64-encoded PEM (SubjectPublicKeyInfo) string."""
    pem_bytes = base64.b64decode(pem_b64)
    return serialization.load_pem_public_key(pem_bytes)


def generate_rsa_private_key() -> rsa.RSAPrivateKey:
    """Generate a fresh 2048-bit RSA private key."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def private_key_to_pem(key: rsa.RSAPrivateKey) -> str:
    """Serialize private key to PEM string."""
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def public_key_to_pem(key: rsa.RSAPrivateKey | rsa.RSAPublicKey) -> str:
    """Serialize a public key to PEM string.

    Accepts either a private key (its public key is derived) or an
    already-public key (serialized directly).
    """
    public_key = key.public_key() if isinstance(key, rsa.RSAPrivateKey) else key
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def compute_kid_from_public(public_key: rsa.RSAPublicKey) -> str:
    """Compute a stable kid from the SHA-256 fingerprint of the public key DER."""
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()[:16]


def compute_kid(key: rsa.RSAPrivateKey) -> str:
    """Compute a stable kid from the SHA-256 fingerprint of the public key DER."""
    return compute_kid_from_public(key.public_key())


def _int_to_b64url(n: int) -> str:
    """Encode a positive integer as unpadded base64url."""
    byte_length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(
        n.to_bytes(byte_length, byteorder="big")
    ).rstrip(b"=").decode("ascii")


def _public_key_to_jwk(public_key: rsa.RSAPublicKey, kid: str, algorithm: str) -> dict:
    """Build a single public JWK entry (no private material: only n and e)."""
    pub = public_key.public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": algorithm,
        "n": _int_to_b64url(pub.n),
        "e": _int_to_b64url(pub.e),
    }


def build_jwks(
    key: rsa.RSAPrivateKey,
    kid: str,
    algorithm: str = "RS256",
    previous_public_key: "rsa.RSAPublicKey | None" = None,
    previous_kid: "str | None" = None,
) -> dict:
    """
    Build a JWKS response dict containing the current public key.

    Key rotation: when ``previous_public_key`` is provided (via the
    JWT_RSA_PREVIOUS_PUBLIC_KEY env var), the previous key is published too,
    each with its own kid, so EXTERNAL verifiers (e.g. Next.js Edge middleware)
    keep accepting tokens signed by the old key during the rotation window.

    Honest limitation: SimpleJWT's VERIFYING_KEY accepts a single key, so
    IN-APP verification only trusts the CURRENT key. After rotating
    JWT_RSA_PRIVATE_KEY, tokens signed by the previous key are rejected by this
    backend itself — in-app sessions require re-login (or a refresh issued
    before the cutover). The previous key here only serves external JWKS
    consumers.
    """
    keys = [_public_key_to_jwk(key.public_key(), kid, algorithm)]
    if previous_public_key is not None:
        keys.append(
            _public_key_to_jwk(
                previous_public_key,
                previous_kid or compute_kid_from_public(previous_public_key),
                algorithm,
            )
        )
    return {"keys": keys}
