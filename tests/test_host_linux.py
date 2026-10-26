import sys

import pytest

from call_switcher.qt import host_linux as host

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux backend")


def _desktop(directory, name, mime="x-scheme-handler/sip;", extra=""):
    path = directory / "applications" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"[Desktop Entry]\nType=Application\nName={name.split('.')[0].title()}\n"
                    f"Exec=true %u\nMimeType={mime}\n{extra}")
    return str(path)


@pytest.fixture
def data_dirs(tmp_path, monkeypatch):
    user, system = tmp_path / "user", tmp_path / "system"
    monkeypatch.setenv("XDG_DATA_HOME", str(user))
    monkeypatch.setenv("XDG_DATA_DIRS", str(system))
    monkeypatch.setattr(host, "in_flatpak", lambda: False)
    return user, system


def test_list_phone_apps(data_dirs):
    user, system = data_dirs
    linphone = _desktop(system, "linphone.desktop", "text/plain;x-scheme-handler/sip;x-scheme-handler/tel")
    _desktop(system, "editor.desktop", "text/plain;")
    _desktop(system, "hidden.desktop", extra="NoDisplay=true\n")
    _desktop(system, f"{host.DESKTOP_ID}", "x-scheme-handler/tel;")
    _desktop(system, "jami.desktop", "x-scheme-handler/callto;")
    override = _desktop(user, "jami.desktop", "x-scheme-handler/callto;")
    _desktop(system / "applications", "kde/softphone.desktop", "x-scheme-handler/sipx;")

    apps = host.list_phone_apps()
    assert apps == [(override, "Jami"), (linphone, "Linphone")]


def test_list_phone_apps_without_dirs(data_dirs):
    assert host.list_phone_apps() == []


def test_desktop_id():
    assert host.desktop_id("/usr/share/applications/kde/org.x.desktop") == "kde-org.x.desktop"
    assert host.desktop_id("/usr/share/applications/linphone.desktop") == "linphone.desktop"


def test_host_prefix(monkeypatch):
    monkeypatch.setattr(host, "in_flatpak", lambda: True)
    assert host.host(["gio", "launch"]) == ["flatpak-spawn", "--host", "gio", "launch"]
    monkeypatch.setattr(host, "in_flatpak", lambda: False)
    assert host.host(["gio", "launch"]) == ["gio", "launch"]


def test_forward_without_app():
    with pytest.raises(host.DialError):
        host.forward_to_app("tel:123", "", lambda message: None)


def test_forward_reports_launch_error(monkeypatch):
    monkeypatch.setattr(host, "in_flatpak", lambda: False)
    errors = []

    class Thread:
        def __init__(self, target, daemon=None):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(host.threading, "Thread", Thread)
    monkeypatch.setattr(host, "_run", lambda cmd, timeout=10: (_ for _ in ()).throw(host.HostError("no gio")))
    host.forward_to_app("tel:123", "/nonexistent.desktop", errors.append)
    assert errors == ["Could not start the phone app: no gio"]
