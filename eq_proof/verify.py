
import json, hashlib, hmac
def _payload(att: dict) -> bytes:
    core = {k:v for k,v in att.items() if k not in ("signature","algo","pubkey")}
    return json.dumps(core, sort_keys=True).encode("utf-8")
def verify_hmac(att: dict, key: str = "DEMO_KEY") -> bool:
    msg=_payload(att); calc=hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return calc == att.get("signature")
def verify_ed25519(att: dict, pubkey_hex: str | None = None) -> bool:
    try:
        import nacl.signing, nacl.encoding  # type: ignore
    except Exception:
        return False
    msg=_payload(att); pk = pubkey_hex or att.get("pubkey"); 
    if not pk: return False
    try:
        vk = nacl.signing.VerifyKey(pk, encoder=nacl.encoding.HexEncoder)  # type: ignore
        vk.verify(msg, bytes.fromhex(att.get("signature",""))); return True
    except Exception: return False
