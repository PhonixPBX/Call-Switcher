import pathlib
import tomllib

from call_switcher import settings


def _values(**overrides):
    return {**settings.DEFAULTS, **overrides}


def test_enabled_modes_in_prompt_order():
    s = _values(appEnabled=True, phonixEnabled=True, ariEnabled=True)
    assert settings.enabled_modes(s) == [settings.MODE_APP, settings.MODE_PHONIX, settings.MODE_ARI]


def test_enabled_modes_none():
    assert settings.enabled_modes(_values(appEnabled=False)) == []


def test_mode_label_uses_app_name():
    s = _values(appPath="/Applications/Telephone.app")
    assert settings.mode_label(settings.MODE_APP, s) == "Telephone"
    assert settings.mode_label(settings.MODE_PHONIX, s) == "PhonixPBX"
    assert settings.mode_label(settings.MODE_ARI, s) == "Asterisk ARI"


def test_mode_label_prefers_app_name():
    s = _values(appPath="/usr/share/applications/org.linphone.Linphone.desktop", appName="Linphone")
    assert settings.mode_label(settings.MODE_APP, s) == "Linphone"


def test_normalize():
    s = settings.normalize({"ariPort": "8089", "ariHTTPS": 1, "ariUser": None, "ariHost": None})
    assert (s["ariPort"], s["ariHTTPS"], s["ariUser"]) == (8089, True, "")
    assert s["phonixURL"] == settings.DEFAULTS["phonixURL"]  # missing -> default
    assert settings.normalize({"ariPort": "abc"})["ariPort"] == 8088


def test_mode_label_without_app():
    assert settings.mode_label(settings.MODE_APP, _values(appPath="")) == "Phone App"


def test_bundle_id_matches_info_plist():
    # The app detects that it runs as the built bundle by comparing these.
    pyproject = tomllib.loads((pathlib.Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert pyproject["tool"]["py2app"]["plist"]["CFBundleIdentifier"] == settings.BUNDLE_ID
