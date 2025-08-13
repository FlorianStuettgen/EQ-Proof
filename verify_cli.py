
#!/usr/bin/env python3
import argparse, json, sys
from eq_proof.verify import verify_hmac, verify_ed25519
def main():
    p=argparse.ArgumentParser(description="Verify EQ-PROOF proof (offline)")
    p.add_argument("proof_json"); p.add_argument("--algo", choices=["auto","ed25519","hmac"], default="auto")
    p.add_argument("--pubkey", default=None); p.add_argument("--hmac-key", default="DEMO_KEY"); args=p.parse_args()
    att=json.load(open(args.proof_json))
    ok=False
    if args.algo in ("auto","ed25519"): ok = verify_ed25519(att, args.pubkey) or ok
    if args.algo in ("auto","hmac"): ok = verify_hmac(att, args.hmac_key) or ok
    print("VERIFIED" if ok else "FAILED"); sys.exit(0 if ok else 2)
if __name__=="__main__": main()
