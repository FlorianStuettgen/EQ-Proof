
import os, json, hashlib, hmac, time, platform
from . import no_net as _no_net  # noqa: F401

def _load_secret() -> bytes:
    key = os.environ.get("EQPROOF_KEY")
    if key: return key.encode("utf-8")
    p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys", "attest_key.txt")
    if os.path.exists(p):
        with open(p,"rb") as f: return f.read().strip() or b"DEMO_KEY"
    return b"DEMO_KEY"

def _try_ed25519_sign(msg: bytes):
    try:
        import nacl.signing, nacl.encoding  # type: ignore
    except Exception:
        return None
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys")
    sk_path = os.path.join(base, "ed25519_sk.hex")
    if not os.path.exists(sk_path): return None
    with open(sk_path,"r") as f: sk_hex=f.read().strip()
    try:
        sk = nacl.signing.SigningKey(sk_hex, encoder=nacl.encoding.HexEncoder)  # type: ignore
        signed = sk.sign(msg)
        pk_hex = sk.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")  # type: ignore
        return {"algo":"ED25519","signature": signed.signature.hex(),"pubkey": pk_hex}
    except Exception:
        return None

def _hash_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def attest(spec: dict, proof: dict, *, spec_path: str = "", inputs_path: str = "") -> dict:
    payload = {
        "spec": spec,
        "proof": proof,
        "meta": {
            "spec_hash": _hash_bytes(json.dumps(spec, sort_keys=True).encode("utf-8")),
            "inputs_hash": _hash_bytes(json.dumps(proof.get("original",{}), sort_keys=True).encode("utf-8")) if proof else "",
            "engine_version": "0.1.0",
            "runtime_env": {"python": platform.python_version(), "platform": platform.platform()}
        },
        "ts": int(time.time())
    }
    msg = json.dumps(payload, sort_keys=True).encode("utf-8")
    ed = _try_ed25519_sign(msg)
    if ed:
        payload.update(ed)
    else:
        sig = hmac.new(_load_secret(), msg, hashlib.sha256).hexdigest()
        payload["signature"]=sig; payload["algo"]="HMAC-SHA256"
    return payload
