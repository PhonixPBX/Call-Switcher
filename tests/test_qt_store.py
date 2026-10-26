import json
import sys

import pytest

if sys.platform == "darwin":
    pytest.skip("Linux and Windows backend", allow_module_level=True)

import keyring.errors  # noqa: E402

from call_switcher import settings  # noqa: E402
from call_switcher.qt import store  # noqa: E402


@pytest.fixture(autouse=True)
def config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path))
    return tmp_path


def test_defaults_without_file():
    s = store.load()
    assert s == {**settings.DEFAULTS, "appPath": "", "loginItem": False}
    assert settings.mode_label(settings.MODE_APP, s) == "Phone App"


def test_save_and_load(config_home):
    store.save({"phonixEnabled": True, "ariPort": 8089, "appPath": "/usr/share/applications/linphone.desktop",
                "appName": "Linphone", "unknown": 1})
    s = store.load()
    assert s["phonixEnabled"] is True
    assert s["ariPort"] == 8089
    assert settings.mode_label(settings.MODE_APP, s) == "Linphone"
    data = json.loads(store._path().read_text())
    assert "unknown" not in data


def test_save_keeps_other_values():
    store.save({"ariHost": "pbx.local"})
    store.save({"loginItem": True})
    s = store.load()
    assert s["ariHost"] == "pbx.local"
    assert s["loginItem"] is True


def test_broken_values_fall_back_to_defaults(config_home):
    path = store._path()
    path.parent.mkdir()
    path.write_text(json.dumps({"ariPort": "abc", "ariUser": None, "ariHTTPS": 1}))
    s = store.load()
    assert (s["ariPort"], s["ariUser"], s["ariHTTPS"]) == (8088, "", True)
    path.write_text("not json")
    assert store.load()["ariPort"] == 8088


def test_secrets(monkeypatch):
    stored = {}

    def delete(service, account):
        if (service, account) not in stored:
            raise keyring.errors.PasswordDeleteError()
        del stored[service, account]

    monkeypatch.setattr(store.keyring, "get_password", lambda service, account: stored.get((service, account)))
    monkeypatch.setattr(store.keyring, "set_password",
                        lambda service, account, secret: stored.__setitem__((service, account), secret))
    monkeypatch.setattr(store.keyring, "delete_password", delete)

    store.set_secret(settings.ACCOUNT_ARI, "secret")
    assert stored == {(settings.BUNDLE_ID, "ari"): "secret"}
    assert store.get_secret(settings.ACCOUNT_ARI) == "secret"
    store.set_secret(settings.ACCOUNT_ARI, "")
    store.set_secret(settings.ACCOUNT_ARI, "")  # deleting twice is fine
    assert store.get_secret(settings.ACCOUNT_ARI) == ""


def test_no_keyring(monkeypatch):
    def fail(*args):
        raise keyring.errors.NoKeyringError()

    monkeypatch.setattr(store.keyring, "get_password", fail)
    monkeypatch.setattr(store.keyring, "set_password", fail)
    assert store.get_secret(settings.ACCOUNT_PHONIX) == ""
    with pytest.raises(keyring.errors.KeyringError):
        store.set_secret(settings.ACCOUNT_PHONIX, "phx_token")
