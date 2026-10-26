"""Windows host with a fake registry, so it runs on every platform."""
import pytest

from call_switcher.qt import host_windows as host

HKCU, HKLM, HKCR = "HKCU", "HKLM", "HKCR"


class FakeRegistry:
    """The few winreg functions host_windows uses, on a {(root, path): {name: value}} dict."""
    HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, HKEY_CLASSES_ROOT = HKCU, HKLM, HKCR
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self, keys):
        self.keys = {(root, path.lower()): values for (root, path), values in keys.items()}

    class Key:
        def __init__(self, values):
            self.values = values

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def OpenKey(self, root, path, reserved=0, access=0):
        if (root, path.lower()) not in self.keys:
            raise FileNotFoundError(path)
        return self.Key(self.keys[root, path.lower()])

    def QueryValueEx(self, key, name):
        if name not in key.values:
            raise FileNotFoundError(name)
        return key.values[name], self.REG_SZ

    def EnumValue(self, key, i):
        items = list(key.values.items())
        if i >= len(items):
            raise OSError("no more data")
        return (*items[i], self.REG_SZ)

    def SetValueEx(self, key, name, reserved, kind, value):
        key.values[name] = value

    def DeleteValue(self, key, name):
        if name not in key.values:
            raise FileNotFoundError(name)
        del key.values[name]


REGISTRY = {
    (HKLM, r"Software\RegisteredApplications"): {
        "MicroSIP": r"Software\MicroSIP\Capabilities",
        "Browser": r"Software\Browser\Capabilities",
        "Call Switcher": r"Software\CallSwitcher\Capabilities",
    },
    (HKLM, r"Software\MicroSIP\Capabilities\URLAssociations"): {"sip": "MicroSIP.URL", "tel": "MicroSIP.URL"},
    (HKLM, r"Software\Browser\Capabilities\URLAssociations"): {"http": "Browser.URL"},
    (HKCU, r"Software\RegisteredApplications"): {"Call Switcher": r"Software\CallSwitcher\Capabilities"},
    (HKCU, r"Software\CallSwitcher\Capabilities\URLAssociations"): {"tel": "CallSwitcher.URL"},
    (HKCR, r"MicroSIP.URL\shell\open\command"): {"": r'"C:\Program Files\MicroSIP\microsip.exe" "%1"'},
    (HKCR, r"CallSwitcher.URL\shell\open\command"): {"": r'"C:\Call Switcher\Call Switcher.exe" "%1"'},
    (HKCR, r"callto\shell\open\command"): {"": r"C:\Old\oldphone.exe %1"},
    (HKCU, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\tel\UserChoice"): {
        "ProgId": "MicroSIP.URL"},
    (HKCU, r"Software\Microsoft\Windows\CurrentVersion\Run"): {},
}


@pytest.fixture
def registry(monkeypatch):
    fake = FakeRegistry(REGISTRY)
    monkeypatch.setattr(host, "_registry", lambda: fake)
    return fake


@pytest.mark.parametrize("template, expected", [
    (r'"C:\a b\phone.exe" "%1"', r'"C:\a b\phone.exe" "tel:+41 44"'),
    (r"C:\phone.exe %1", r'C:\phone.exe "tel:+41 44"'),
    (r'"C:\phone.exe" -call "%L" %*', r'"C:\phone.exe" -call "tel:+41 44"'),
    (r'"C:\phone.exe"', r'"C:\phone.exe" "tel:+41 44"'),
])
def test_expand_command(template, expected):
    assert host.expand_command(template, "tel:+41 44") == expected


def test_expand_command_keeps_percent_in_url():
    assert host.expand_command('x.exe "%1"', 'tel:%2B41"') == 'x.exe "tel:%2B41"'


def test_list_phone_apps(registry):
    assert host.list_phone_apps() == [("MicroSIP.URL", "MicroSIP"), ("callto", "oldphone")]


def test_default_handler(registry):
    assert host.default_handler() == "MicroSIP.URL"


def test_forward_to_app(registry, monkeypatch):
    started = []
    monkeypatch.setattr(host.subprocess, "Popen", lambda command, **kwargs: started.append(command))
    host.forward_to_app("tel:0441234567", "MicroSIP.URL", lambda message: None)
    assert started == [r'"C:\Program Files\MicroSIP\microsip.exe" "tel:0441234567"']
    with pytest.raises(host.DialError):
        host.forward_to_app("tel:0441234567", "Gone.URL", lambda message: None)
    with pytest.raises(host.DialError):
        host.forward_to_app("tel:0441234567", "", lambda message: None)


def test_autostart(registry, monkeypatch):
    monkeypatch.setattr(host.sys, "executable", r"C:\Call Switcher\Call Switcher.exe")
    run = registry.keys[HKCU, host.RUN_KEY.lower()]
    host.request_autostart(True)
    assert run == {"Call Switcher": r'"C:\Call Switcher\Call Switcher.exe" --background'}
    host.request_autostart(False)
    host.request_autostart(False)
    assert run == {}
