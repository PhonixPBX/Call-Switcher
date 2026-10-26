import os
import sys

from .i18n import _

BUNDLE_ID = "org.phonixpbx.callswitcher"
ACCOUNT_ARI = "ari"
ACCOUNT_PHONIX = "phonix"

MODE_APP = "app"
MODE_ARI = "ari"
MODE_PHONIX = "phonix"

# Order of the methods in the settings and in the "which method?" prompt.
MODES = (MODE_APP, MODE_PHONIX, MODE_ARI)
ENABLED_KEYS = {MODE_APP: "appEnabled", MODE_PHONIX: "phonixEnabled", MODE_ARI: "ariEnabled"}

DEFAULTS = {
    "appEnabled": True,
    "phonixEnabled": False,
    "ariEnabled": False,
    "appPath": "/Applications/Telephone.app",
    # Display name of the phone app; only set on Linux, where appPath is a .desktop file.
    "appName": "",
    "ariHost": "192.168.1.100",
    "ariPort": 8088,
    "ariHTTPS": False,
    "ariUser": "",
    "ariEndpoint": "PJSIP/100",
    "ariContext": "from-internal",
    "ariCallerId": "",
    "phonixURL": "https://",
    "phonixExtension": "",
    "phonixInsecure": False,
}


def _backend():
    if sys.platform == "darwin":
        from . import macos as backend
    else:
        from .linux import store as backend
    return backend


def normalize(raw: dict) -> dict:
    """Stored values (any type, None if missing) -> the types of DEFAULTS."""
    s = {}
    for key, default in DEFAULTS.items():
        value = raw.get(key, default)
        if isinstance(default, bool):
            s[key] = bool(value)
        elif isinstance(default, int):
            try:
                s[key] = int(value)
            except (TypeError, ValueError):
                s[key] = default
        else:
            s[key] = str(value or "")
    return s


def load() -> dict:
    return _backend().load()


def save(values: dict):
    _backend().save(values)


def get_secret(account: str) -> str:
    return _backend().get_secret(account)


def set_secret(account: str, secret: str):
    _backend().set_secret(account, secret)


def enabled_modes(s: dict) -> list[str]:
    return [mode for mode in MODES if s[ENABLED_KEYS[mode]]]


def mode_label(mode: str, s: dict) -> str:
    if mode == MODE_APP:
        return s.get("appName") or os.path.splitext(os.path.basename(s["appPath"]))[0] or _("Phone App")
    return {MODE_PHONIX: "PhonixPBX", MODE_ARI: "Asterisk ARI"}[mode]
