"""Linux and Windows backend: settings as JSON in the user's config dir, secrets in the
Secret Service (Linux) or the Windows Credential Manager, both through keyring."""
import json
import os
import pathlib
import sys

import keyring
import keyring.errors

from .. import settings

# A .desktop file (Linux) or ProgID (Windows) chosen in the settings; there is no default phone app.
DEFAULTS = {**settings.DEFAULTS, "appPath": "", "loginItem": False}


def _path() -> pathlib.Path:
    if sys.platform == "win32":
        return pathlib.Path(os.environ["APPDATA"]) / "Call Switcher" / "settings.json"
    config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return pathlib.Path(config) / "call-switcher" / "settings.json"


def _read() -> dict:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load() -> dict:
    data = {**DEFAULTS, **_read()}
    return {**settings.normalize(data), "loginItem": bool(data["loginItem"])}


def save(values: dict):
    data = {**_read(), **{k: v for k, v in values.items() if k in DEFAULTS}}
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def get_secret(account: str) -> str:
    try:
        return keyring.get_password(settings.BUNDLE_ID, account) or ""
    except keyring.errors.KeyringError:
        return ""


def set_secret(account: str, secret: str):
    if not secret:
        try:
            keyring.delete_password(settings.BUNDLE_ID, account)
        except keyring.errors.PasswordDeleteError:
            pass
        return
    keyring.set_password(settings.BUNDLE_ID, account, secret)
