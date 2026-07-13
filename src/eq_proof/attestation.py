"""Ed25519 key handling and proof payload attestation."""

from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_json_bytes, sha256_hex
from .errors import InvalidProof


def _atomic_write(path: str | Path, data: bytes, mode: int | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary_name, mode)
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def generate_keypair(
    private_path: str | Path,
    public_path: str | Path,
    *,
    force: bool = False,
) -> None:
    private_file = Path(private_path)
    public_file = Path(public_path)
    if not force and (private_file.exists() or public_file.exists()):
        raise FileExistsError("Refusing to overwrite an existing key; pass force=True to replace it")
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _atomic_write(private_file, private_bytes, 0o600)
    _atomic_write(public_file, public_bytes, 0o644)


def _load_private_key(path: str | Path) -> Ed25519PrivateKey:
    try:
        key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    except (OSError, ValueError) as exc:
        raise InvalidProof(f"Unable to load Ed25519 private key: {exc}") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise InvalidProof("Private key is not Ed25519")
    return key


def _load_public_key(path: str | Path) -> Ed25519PublicKey:
    try:
        key = serialization.load_pem_public_key(Path(path).read_bytes())
    except (OSError, ValueError) as exc:
        raise InvalidProof(f"Unable to load Ed25519 public key: {exc}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise InvalidProof("Public key is not Ed25519")
    return key


def _raw_public_key(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _fingerprint(public_key: Ed25519PublicKey) -> str:
    return sha256_hex(
        {"ed25519_public_key": base64.b64encode(_raw_public_key(public_key)).decode("ascii")}
    )


def attest_core(core: dict[str, Any], private_key_path: str | Path | None) -> dict[str, Any]:
    payload_digest = sha256_hex(core)
    if private_key_path is None:
        return {
            "mode": "digest-only",
            "payload_sha256": payload_digest,
            "warning": "Integrity only; no signer identity is asserted.",
        }

    private_key = _load_private_key(private_key_path)
    public_key = private_key.public_key()
    signature = private_key.sign(canonical_json_bytes(core))
    return {
        "mode": "Ed25519",
        "payload_sha256": payload_digest,
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "public_key_base64": base64.b64encode(_raw_public_key(public_key)).decode("ascii"),
        "signer_fingerprint_sha256": _fingerprint(public_key),
        "trust_note": (
            "Verification proves possession of this key. Identity requires an "
            "independently trusted fingerprint."
        ),
    }


def verify_attestation(
    core: dict[str, Any],
    attestation: dict[str, Any],
    public_key_path: str | Path | None,
) -> tuple[bool | None, str | None]:
    if attestation.get("payload_sha256") != sha256_hex(core):
        raise InvalidProof("Payload digest mismatch")

    mode = attestation.get("mode")
    if mode == "digest-only":
        if public_key_path is not None:
            raise InvalidProof("A public key was supplied for a digest-only proof")
        return None, None
    if mode != "Ed25519":
        raise InvalidProof(f"Unsupported attestation mode: {mode!r}")

    try:
        embedded_raw = base64.b64decode(attestation["public_key_base64"], validate=True)
        signature = base64.b64decode(attestation["signature_base64"], validate=True)
        embedded_key = Ed25519PublicKey.from_public_bytes(embedded_raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidProof("Malformed Ed25519 attestation") from exc

    verification_key = _load_public_key(public_key_path) if public_key_path else embedded_key
    if public_key_path and _raw_public_key(verification_key) != embedded_raw:
        raise InvalidProof("Embedded public key does not match the trusted public key")
    fingerprint = _fingerprint(verification_key)
    if attestation.get("signer_fingerprint_sha256") != fingerprint:
        raise InvalidProof("Signer fingerprint mismatch")
    try:
        verification_key.verify(signature, canonical_json_bytes(core))
    except InvalidSignature as exc:
        raise InvalidProof("Ed25519 signature verification failed") from exc
    return True, fingerprint
