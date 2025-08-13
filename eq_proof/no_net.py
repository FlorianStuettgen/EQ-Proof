
import os, socket
class _NoNetSocket(socket.socket):
    def connect(self, *a, **k): raise RuntimeError("Outbound network disabled by eq_proof.no_net")
    def connect_ex(self, *a, **k): raise RuntimeError("Outbound network disabled by eq_proof.no_net")
def enforce():
    if os.environ.get("EQPROOF_ALLOW_NET","0") not in ("1","true","True"):
        socket.socket = _NoNetSocket  # type: ignore
        def _deny(*a, **k): raise RuntimeError("Outbound network disabled by eq_proof.no_net")
        socket.create_connection = _deny  # type: ignore
enforce()
