import pytest

from call_switcher import dialer, main, settings, ui


@pytest.fixture
def delegate(monkeypatch):
    """AppDelegate with dialing, dialogs and settings stubbed out; records what happens."""
    events = []
    monkeypatch.setattr(dialer, "forward_to_app", lambda url, path, on_error: events.append(("app", url)))
    monkeypatch.setattr(dialer, "originate_phonix", lambda number, s, token: events.append(("phonix", number)))
    monkeypatch.setattr(dialer, "originate_ari", lambda number, s, password: events.append(("ari", number)))
    monkeypatch.setattr(settings, "get_secret", lambda account: "secret")
    monkeypatch.setattr(ui, "show_alert", lambda *args: events.append(("alert", args[0])))

    class Thread:  # run "background" dialing inline
        def __init__(self, target, daemon=None):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(main.threading, "Thread", Thread)

    d = main.AppDelegate.alloc().init()
    d.events = events
    monkeypatch.setattr(d, "showSettings", lambda: events.append(("settings",)), raising=False)
    return d


def _configure(monkeypatch, enabled, answer=None):
    s = {**settings.DEFAULTS, "appEnabled": "app" in enabled,
         "phonixEnabled": "phonix" in enabled, "ariEnabled": "ari" in enabled}
    monkeypatch.setattr(settings, "load", lambda: s)
    asked = []
    monkeypatch.setattr(ui, "choose_method", lambda number, choices: asked.append(choices) or answer)
    return asked


def test_single_method_dials_without_asking(monkeypatch, delegate):
    asked = _configure(monkeypatch, {"phonix"})
    delegate.dial("tel:0441234567")
    assert asked == []
    assert delegate.events == [("phonix", "0441234567")]


def test_several_methods_ask_every_time(monkeypatch, delegate):
    asked = _configure(monkeypatch, {"app", "phonix"}, answer=settings.MODE_APP)
    delegate.dial("tel:0441234567")
    delegate.dial("tel:0441234567")
    assert len(asked) == 2
    assert [label for _, label in asked[0]] == ["Telephone", "PhonixPBX"]
    assert delegate.events == [("app", "tel:0441234567")] * 2
    assert delegate.last_call == "0441234567 (Telephone)"


def test_cancel_in_prompt_does_not_dial(monkeypatch, delegate):
    _configure(monkeypatch, {"app", "ari"}, answer=None)
    delegate.dial("tel:0441234567")
    assert delegate.events == []


def test_no_method_enabled(monkeypatch, delegate):
    _configure(monkeypatch, set())
    delegate.dial("tel:0441234567")
    assert delegate.events == [("alert", "No calling method enabled"), ("settings",)]


def test_invalid_number(monkeypatch, delegate):
    _configure(monkeypatch, {"phonix"})
    delegate.dial("tel:abc")
    assert delegate.events == [("alert", "Not a valid number")]


def test_dial_error_is_shown(monkeypatch, delegate):
    _configure(monkeypatch, {"phonix"})

    def fail(number, s, token):
        raise dialer.DialError("API-Token ungültig")

    monkeypatch.setattr(dialer, "originate_phonix", fail)
    shown = []
    monkeypatch.setattr(main.AppHelper, "callAfter", lambda fn, *args: shown.append(args))
    delegate.dial("tel:0441234567")
    assert shown == [("Call failed", "API-Token ungültig")]
