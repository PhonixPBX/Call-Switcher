import pytest

from call_switcher import calls, dialer, settings


class FakeUI:
    def __init__(self, events):
        self.events = events
        self.asked = []
        self.answer = None

    def show_alert(self, title, text=""):
        self.events.append(("alert", title))

    def choose_method(self, number, choices):
        self.asked.append(choices)
        return self.answer


class Phone:
    """place_call with dialing, dialogs and settings stubbed out; records what happens."""

    def __init__(self, monkeypatch):
        self.events = []
        self.errors = []
        self.last_call = None
        self.ui = FakeUI(self.events)
        monkeypatch.setattr(dialer, "originate_phonix", lambda number, s, token: self.events.append(("phonix", number)))
        monkeypatch.setattr(dialer, "originate_ari", lambda number, s, password: self.events.append(("ari", number)))
        monkeypatch.setattr(settings, "get_secret", lambda account: "secret")

        class Thread:  # run "background" dialing inline
            def __init__(self, target, daemon=None):
                self.target = target

            def start(self):
                self.target()

        monkeypatch.setattr(calls.threading, "Thread", Thread)

    def forward_to_app(self, url, path, on_error):
        self.events.append(("app", url))

    def dial(self, url):
        self.last_call = calls.place_call(url, self.ui, self.forward_to_app,
                                          lambda: self.events.append(("settings",)), self.errors.append)


@pytest.fixture
def phone(monkeypatch):
    return Phone(monkeypatch)


def _configure(monkeypatch, phone, enabled, answer=None):
    s = {**settings.DEFAULTS, "appEnabled": "app" in enabled,
         "phonixEnabled": "phonix" in enabled, "ariEnabled": "ari" in enabled}
    monkeypatch.setattr(settings, "load", lambda: s)
    phone.ui.answer = answer
    return phone.ui.asked


def test_single_method_dials_without_asking(monkeypatch, phone):
    asked = _configure(monkeypatch, phone, {"phonix"})
    phone.dial("tel:0441234567")
    assert asked == []
    assert phone.events == [("phonix", "0441234567")]


def test_several_methods_ask_every_time(monkeypatch, phone):
    asked = _configure(monkeypatch, phone, {"app", "phonix"}, answer=settings.MODE_APP)
    phone.dial("tel:0441234567")
    phone.dial("tel:0441234567")
    assert len(asked) == 2
    assert [label for _, label in asked[0]] == ["Telephone", "PhonixPBX"]
    assert phone.events == [("app", "tel:0441234567")] * 2
    assert phone.last_call == "0441234567 (Telephone)"


def test_cancel_in_prompt_does_not_dial(monkeypatch, phone):
    _configure(monkeypatch, phone, {"app", "ari"}, answer=None)
    phone.dial("tel:0441234567")
    assert phone.events == []
    assert phone.last_call is None


def test_no_method_enabled(monkeypatch, phone):
    _configure(monkeypatch, phone, set())
    phone.dial("tel:0441234567")
    assert phone.events == [("alert", "No calling method enabled"), ("settings",)]


def test_invalid_number(monkeypatch, phone):
    _configure(monkeypatch, phone, {"phonix"})
    phone.dial("tel:abc")
    assert phone.events == [("alert", "Not a valid number")]


def test_dial_error_is_reported(monkeypatch, phone):
    _configure(monkeypatch, phone, {"phonix"})

    def fail(number, s, token):
        raise dialer.DialError("API-Token ungültig")

    monkeypatch.setattr(dialer, "originate_phonix", fail)
    phone.dial("tel:0441234567")
    assert phone.errors == ["API-Token ungültig"]


def test_app_error_is_reported(monkeypatch, phone):
    _configure(monkeypatch, phone, {"app"})

    def fail(url, path, on_error):
        raise dialer.DialError("Phone app not found")

    phone.forward_to_app = fail
    phone.dial("tel:0441234567")
    assert phone.errors == ["Phone app not found"]


@pytest.mark.parametrize("text, expected", [
    (" +41 44 123 45 67\n", "+41 44 123 45 67"),
    ("(044) 123-45-67", "(044) 123-45-67"),
    ("12", ""),
    ("hello", ""),
])
def test_clipboard_number(text, expected):
    assert calls.clipboard_number(text) == expected
