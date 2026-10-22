import os
import subprocess

from Foundation import NSUserDefaults
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


def _defaults():
    d = NSUserDefaults.standardUserDefaults()
    d.registerDefaults_(DEFAULTS)
    return d


def load() -> dict:
    d = _defaults()
    s = {}
    for key, default in DEFAULTS.items():
        value = d.objectForKey_(key)
        if isinstance(default, bool):
            s[key] = bool(value)
        elif isinstance(default, int):
            s[key] = int(value)
        else:
            s[key] = str(value or "")
    return s


def save(values: dict):
    d = _defaults()
    for key, value in values.items():
        if key in DEFAULTS:
            d.setObject_forKey_(value, key)


def enabled_modes(s: dict) -> list[str]:
    return [mode for mode in MODES if s[ENABLED_KEYS[mode]]]


def mode_label(mode: str, s: dict) -> str:
    if mode == MODE_APP:
        return os.path.splitext(os.path.basename(s["appPath"]))[0] or _("Phone App")
    return {MODE_PHONIX: "PhonixPBX", MODE_ARI: "Asterisk ARI"}[mode]


def get_secret(account: str) -> str:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password",
         "-s", BUNDLE_ID, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def set_secret(account: str, secret: str):
    if not secret:
        subprocess.run(
            ["/usr/bin/security", "delete-generic-password",
             "-s", BUNDLE_ID, "-a", account],
            capture_output=True,
        )
        return
    subprocess.run(
        ["/usr/bin/security", "add-generic-password", "-U",
         "-s", BUNDLE_ID, "-a", account, "-l", f"Call Switcher {account}",
         "-w", secret],
        capture_output=True, check=True,
    )
