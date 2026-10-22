import ssl
import urllib.parse

import pytest

from call_switcher import dialer


@pytest.mark.parametrize("url, number", [
    ("tel:+41441234567", "+41441234567"),
    ("tel:+41%2044%20123%2045%2067", "+41441234567"),
    ("tel:+41-44-123;phone-context=example.com", "+4144123"),
    ("callto://0441234567", "0441234567"),
    ("sip:101@pbx.local", "101"),
    ("tel:*97#", "*97#"),
    ("0441234567", "0441234567"),
    ("tel:abc", ""),
])
def test_extract_number(url, number):
    assert dialer.extract_number(url) == number


@pytest.mark.parametrize("body, detail", [
    (b'{"detail": "token may not place calls"}', "token may not place calls"),
    (b'{"detail": {"message": "", "fields": {"extension": "the phone is disabled"}}}',
     "extension: the phone is disabled"),
    (b'{"detail": [{"msg": "Field required"}, {"msg": "Too long"}]}', "Field required; Too long"),
    (b'{"message": "Endpoint not found"}', "Endpoint not found"),
    (b"not json", ""),
    (b"[]", ""),
])
def test_error_detail(body, detail):
    assert dialer._error_detail(body) == detail


def test_ssl_context_insecure_skips_verification():
    assert dialer._ssl_context(True).verify_mode == ssl.CERT_NONE
    assert dialer._ssl_context(False).verify_mode == ssl.CERT_REQUIRED


def test_unreachable_host():
    s = {"phonixURL": "http://127.0.0.1:9", "phonixExtension": "100", "phonixInsecure": False}
    with pytest.raises(dialer.DialError, match="is not reachable"):
        dialer.originate_phonix("0441234567", s, "phx_calls")


# --- PhonixPBX ----------------------------------------------------------------

def test_phonix_originate(server, phonix_settings):
    dialer.originate_phonix("+41441234567", phonix_settings, "phx_calls")
    method, path, auth, body = server.requests[-1]
    assert (method, path, auth) == ("POST", "/api/v1/calls", "Bearer phx_calls")
    assert body == {"extension": "100", "number": "+41441234567"}


def test_phonix_url_trailing_slash(server, phonix_settings):
    dialer.originate_phonix("0441234567", {**phonix_settings, "phonixURL": server.url + "/"}, "phx_calls")
    assert server.requests[-1][1] == "/api/v1/calls"


def test_phonix_test_ok(server, phonix_settings):
    assert dialer.test_phonix(phonix_settings, "phx_calls") == "Connected to PhonixPBX 1.8.0"
    # The permission check posts an empty body, which can never place a call.
    calls = [r for r in server.requests if r[1] == "/api/v1/calls"]
    assert [r[3] for r in calls] == [{}]


@pytest.mark.parametrize("token, settings_override, message", [
    ("phx_wrong", {}, "API token is invalid"),
    ("phx_nocalls", {}, "May place calls"),
    ("phx_calls", {"phonixExtension": "999"}, "no phone with extension 999"),
    ("", {}, "No API token"),
    ("phx_calls", {"phonixURL": "pbx.local"}, "server URL"),
])
def test_phonix_test_errors(phonix_settings, token, settings_override, message):
    with pytest.raises(dialer.DialError, match=message):
        dialer.test_phonix({**phonix_settings, **settings_override}, token)


def test_phonix_originate_unknown_extension(phonix_settings):
    with pytest.raises(dialer.DialError, match="no phone with extension '999'"):
        dialer.originate_phonix("0441234567", {**phonix_settings, "phonixExtension": "999"}, "phx_calls")


# --- Asterisk ARI ---------------------------------------------------------------

def test_ari_originate(server, ari_settings):
    dialer.originate_ari("+41441234567", {**ari_settings, "ariCallerId": "Rene <100>"}, "secret")
    method, path, auth, _ = server.requests[-1]
    url = urllib.parse.urlsplit(path)
    assert (method, url.path) == ("POST", "/ari/channels")
    assert urllib.parse.parse_qs(url.query) == {
        "endpoint": ["PJSIP/100"],
        "context": ["from-internal"],
        "extension": ["+41441234567"],
        "priority": ["1"],
        "callerId": ["Rene <100>"],
    }
    assert auth == "Basic dXNlcjpzZWNyZXQ="


def test_ari_test(ari_settings):
    assert dialer.test_ari(ari_settings, "secret") == "Connected to Asterisk 22.1.0"


def test_ari_wrong_password(ari_settings):
    with pytest.raises(dialer.DialError, match="Login failed"):
        dialer.test_ari(ari_settings, "wrong")
