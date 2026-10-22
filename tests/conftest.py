import http.server
import json
import threading

import pytest

from call_switcher import i18n

# Tests check the English source texts; translations are covered in test_i18n.py.
i18n.set_language("en")

PHONIX_TOKENS = {"phx_calls": True, "phx_nocalls": False}
PHONIX_PHONES = [{"extension": "100"}, {"extension": "101"}]


class FakeServer(http.server.ThreadingHTTPServer):
    """Records requests; answers like PhonixPBX (/api/v1/...) or Asterisk ARI (/ari/...)."""

    def __init__(self):
        super().__init__(("127.0.0.1", 0), FakeHandler)
        self.requests = []

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"


class FakeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        self.server.requests.append((self.command, self.path, self.headers.get("Authorization"), body))
        if self.path.startswith("/ari/"):
            return self._ari()
        return self._phonix(body)

    do_GET = do_POST = _handle

    def _ari(self):
        if self.headers.get("Authorization") != "Basic dXNlcjpzZWNyZXQ=":  # user:secret
            return self._send(401, {"message": "Authentication required"})
        if self.path == "/ari/asterisk/info":
            return self._send(200, {"system": {"version": "22.1.0"}})
        return self._send(200, {"id": "channel-1"})

    def _phonix(self, body):
        token = (self.headers.get("Authorization") or "").removeprefix("Bearer ")
        if token not in PHONIX_TOKENS:
            return self._send(401, {"detail": "invalid, disabled or expired token"})
        if self.command == "GET" and self.path == "/api/v1/status":
            return self._send(200, {"system": {"version": "1.8.0"}, "asterisk": {}})
        if self.command == "GET" and self.path == "/api/v1/phones":
            return self._send(200, PHONIX_PHONES)
        if self.command == "POST" and self.path == "/api/v1/calls":
            if not PHONIX_TOKENS[token]:
                return self._send(403, {"detail": "token may not place calls"})
            if not body or "extension" not in body or "number" not in body:
                return self._send(422, {"detail": [{"msg": "Field required"}]})
            if body["extension"] not in {p["extension"] for p in PHONIX_PHONES}:
                return self._send(404, {"detail": f"no phone with extension {body['extension']!r}"})
            return self._send(202, {**body, "status": "ringing"})
        return self._send(404, {"detail": "Not Found"})


@pytest.fixture
def server():
    srv = FakeServer()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def phonix_settings(server):
    return {"phonixURL": server.url, "phonixExtension": "100", "phonixInsecure": False}


@pytest.fixture
def ari_settings(server):
    return {
        "ariHost": "127.0.0.1",
        "ariPort": server.server_port,
        "ariHTTPS": False,
        "ariUser": "user",
        "ariEndpoint": "PJSIP/100",
        "ariContext": "from-internal",
        "ariCallerId": "",
    }
