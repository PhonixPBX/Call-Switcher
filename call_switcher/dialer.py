import base64
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

import truststore
from .i18n import _

SCHEMES = ("tel", "callto", "sip")


class DialError(Exception):
    pass


class HTTPStatusError(DialError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def extract_number(url: str) -> str:
    """'tel:+41 44 123', 'callto://0441234567', 'sip:101@pbx' -> digits, '+', '*', '#'."""
    raw = url.split(":", 1)[1] if ":" in url else url
    raw = urllib.parse.unquote(raw).lstrip("/")
    raw = re.split(r"[;?@]", raw, maxsplit=1)[0]
    return re.sub(r"[^0-9+*#]", "", raw)


def _ssl_context(insecure: bool) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    # The bundled OpenSSL has no CA store; verify against the system trust store instead.
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _error_detail(body: bytes) -> str:
    """FastAPI/ARI error bodies: {"detail": str | {"message", "fields"} | [...]} or {"message": str}."""
    try:
        data = json.loads(body)
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""
    detail = data.get("detail", data.get("message", ""))
    if isinstance(detail, dict):
        fields = ", ".join(f"{k}: {v}" for k, v in (detail.get("fields") or {}).items())
        return detail.get("message") or fields
    if isinstance(detail, list):
        return "; ".join(str(e.get("msg", e)) if isinstance(e, dict) else str(e) for e in detail)
    return str(detail)


def _request(url: str, method: str, headers: dict, body: dict | None = None, insecure: bool = False):
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    context = _ssl_context(insecure) if url.startswith("https:") else None

    host = urllib.parse.urlsplit(url).netloc
    try:
        with urllib.request.urlopen(req, timeout=5, context=context) as response:
            payload = response.read()
            return json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        try:
            detail = _error_detail(e.read())
        except OSError:
            detail = ""
        raise HTTPStatusError(e.code, detail or str(e.reason)) from e
    except urllib.error.URLError as e:
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            raise DialError(_("The certificate of {host} is not trusted "
                              "(enable “Don’t verify certificate” if needed).", host=host)) from e
        raise DialError(_("{host} is not reachable: {reason}", host=host, reason=e.reason)) from e
    except OSError as e:
        raise DialError(_("{host} is not reachable: {reason}", host=host, reason=e)) from e


# --- Asterisk ARI -----------------------------------------------------------

def _ari_request(s: dict, password: str, method: str, path: str, params: dict | None = None):
    scheme = "https" if s["ariHTTPS"] else "http"
    url = f"{scheme}://{s['ariHost']}:{s['ariPort']}/ari{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    auth = base64.b64encode(f"{s['ariUser']}:{password}".encode()).decode()

    try:
        return _request(url, method, {"Authorization": f"Basic {auth}"})
    except HTTPStatusError as e:
        if e.code == 401:
            raise DialError(_("Login failed (check user and password).")) from e
        raise DialError(_("ARI error {code}: {detail}", code=e.code, detail=e)) from e


def originate_ari(number: str, s: dict, password: str):
    """Ring our own endpoint first; once answered, Asterisk dials `number` in `context`."""
    params = {
        "endpoint": s["ariEndpoint"],
        "context": s["ariContext"],
        "extension": number,
        "priority": "1",
    }
    if s["ariCallerId"]:
        params["callerId"] = s["ariCallerId"]
    _ari_request(s, password, "POST", "/channels", params)


def test_ari(s: dict, password: str) -> str:
    info = _ari_request(s, password, "GET", "/asterisk/info") or {}
    version = info.get("system", {}).get("version", "")
    return _("Connected to Asterisk {version}", version=version).strip()


# --- PhonixPBX click-to-call (POST /api/v1/calls) ---------------------------

def _phonix_request(s: dict, token: str, method: str, path: str, body: dict | None = None):
    base = s["phonixURL"].strip().rstrip("/")
    if not re.match(r"https?://.+", base):
        raise DialError(_("Please enter a server URL like https://pbx.example.com."))
    if not token:
        raise DialError(_("No API token configured."))
    try:
        return _request(f"{base}/api/v1{path}", method, {"Authorization": f"Bearer {token}"},
                        body, insecure=s["phonixInsecure"])
    except HTTPStatusError as e:
        if e.code == 401:
            raise DialError(_("API token is invalid, disabled or expired.")) from e
        if e.code == 403 and "place calls" in str(e):
            raise DialError(_("The API token lacks the “May place calls” option.")) from e
        if e.code == 404:
            raise DialError(f"Phonix: {e}") from e
        if e.code == 429:
            raise DialError(_("Too many failed logins – please try again later.")) from e
        raise DialError(_("PhonixPBX error {code}: {detail}", code=e.code, detail=e)) from e


def originate_phonix(number: str, s: dict, token: str):
    """Phonix rings the phone, then dials `number` with the phone's outgoing rules and caller ID."""
    _phonix_request(s, token, "POST", "/calls", {"extension": s["phonixExtension"], "number": number})


def test_phonix(s: dict, token: str) -> str:
    """Checks token, call permission and extension without placing a call."""
    status = _phonix_request(s, token, "GET", "/status") or {}

    # Auth runs before body validation: an empty body answers 403 without call permission, else 422.
    try:
        _phonix_request(s, token, "POST", "/calls", {})
    except DialError as e:
        cause = e.__cause__
        if not (isinstance(cause, HTTPStatusError) and cause.code == 422):
            raise

    extension = s["phonixExtension"]
    phones = _phonix_request(s, token, "GET", "/phones") or []
    if isinstance(phones, list) and phones and not any(str(p.get("extension")) == extension for p in phones):
        raise DialError(_("Token OK, but there is no phone with extension {extension}.",
                          extension=extension or _("(empty)")))

    version = (status.get("system") or {}).get("version", "") if isinstance(status, dict) else ""
    return _("Connected to PhonixPBX {version}", version=version).strip()
