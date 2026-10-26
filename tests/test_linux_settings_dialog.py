import os
import sys

import pytest

if sys.platform != "linux":
    pytest.skip("Linux frontend", allow_module_level=True)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from call_switcher import i18n, settings  # noqa: E402
from call_switcher.linux import host, settings_dialog, ui  # noqa: E402

APPS = [("/usr/share/applications/linphone.desktop", "Linphone"), ("/usr/share/applications/jami.desktop", "Jami")]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(host, "list_phone_apps", lambda: APPS)
    monkeypatch.setattr(host, "default_handler", lambda: "linphone.desktop")
    monkeypatch.setattr(settings, "get_secret", lambda account: "")
    monkeypatch.setattr(settings, "set_secret", lambda account, secret: None)
    alerts = []
    monkeypatch.setattr(ui, "show_alert", lambda title, text="": alerts.append(title))
    d = settings_dialog.SettingsDialog()
    d.alerts = alerts
    d.show_settings()
    yield d
    d.close()


def _layout(d):
    d.adjustSize()
    field = d.mode_picker.mapTo(d, d.mode_picker.rect().topLeft()).x()
    return d.size().width(), d.size().height(), field


def test_only_selected_method_is_visible(dialog):
    dialog.mode_picker.setCurrentIndex(settings.MODES.index(settings.MODE_PHONIX))
    assert dialog.phonix_url.isVisible()
    assert not dialog.host.isVisible()
    assert not dialog.app.isVisible()


@pytest.mark.parametrize("language", i18n.LANGUAGES)
def test_layout_fits_in_every_language(qapp, dialog, language, monkeypatch):
    i18n.set_language(language)
    try:
        d = settings_dialog.SettingsDialog()
        d.show_settings()
        layouts = set()
        for mode in settings.MODES:
            d.mode_picker.setCurrentIndex(settings.MODES.index(mode))
            qapp.processEvents()
            layouts.add(_layout(d))
            assert d.width() < 800, f"{language}/{mode}: window too wide ({d.width()})"
        # Switching methods must not resize the window or move the fields.
        assert len(layouts) == 1, layouts
        d.close()
    finally:
        i18n.set_language("en")


def test_phone_apps_and_handler(dialog):
    assert [dialog.app.itemText(i) for i in range(dialog.app.count())] == ["Linphone", "Jami"]
    assert dialog.handler_label.text() == "opens with: Linphone"


def test_missing_app_is_kept(dialog):
    settings.save({"appPath": "/opt/old/softphone.desktop", "appName": "Old Phone"})
    dialog.show_settings()
    assert dialog.app.currentText() == "Old Phone"
    assert dialog._form_values()["appPath"] == "/opt/old/softphone.desktop"


def test_enabled_checkboxes_go_into_form_values(dialog):
    for mode, checkbox in dialog.enabled.items():
        checkbox.setChecked(mode == settings.MODE_ARI)
    assert settings.enabled_modes(dialog._form_values()) == [settings.MODE_ARI]
    assert dialog.mode_picker.tabText(settings.MODES.index(settings.MODE_ARI)) == "✓ Asterisk ARI"


def test_save_validates(dialog):
    for checkbox in dialog.enabled.values():
        checkbox.setChecked(False)
    dialog._save()
    dialog.enabled[settings.MODE_PHONIX].setChecked(True)
    dialog.phonix_extension.setText("")
    dialog._save()
    assert dialog.alerts == ["No method enabled.", "No extension entered"]
    assert dialog.isVisible()


def test_save(dialog):
    dialog.app.setCurrentIndex(1)
    dialog.phonix_extension.setText("100")
    dialog.enabled[settings.MODE_PHONIX].setChecked(True)
    dialog._save()
    assert dialog.alerts == []
    assert not dialog.isVisible()
    s = settings.load()
    assert (s["appPath"], s["appName"], s["phonixEnabled"]) == (APPS[1][0], "Jami", True)
    assert settings.mode_label(settings.MODE_APP, s) == "Jami"
