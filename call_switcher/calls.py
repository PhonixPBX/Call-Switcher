"""Placing a call from a tel:/callto:/sip: URL; shared by the macOS and the Linux app."""
import re
import threading

from . import dialer, settings
from .i18n import _


def clipboard_number(text: str) -> str:
    """Clipboard text if it looks like a phone number (suggested in "Dial Number"), else ''."""
    text = text.strip()
    return text if re.fullmatch(r"[0-9+*#()/.\s-]{3,30}", text) else ""


def place_call(url: str, ui, forward_to_app, show_settings, on_error) -> str | None:
    """Dial `url` with the enabled method, asking which one if several are enabled.

    `ui` provides show_alert() and choose_method(); `on_error(message)` is called from a
    background thread. Returns the "last call" text, or None if nothing was dialed.
    """
    number = dialer.extract_number(url)
    if not number:
        ui.show_alert(_("Not a valid number"), url)
        return None
    s = settings.load()

    modes = settings.enabled_modes(s)
    if not modes:
        ui.show_alert(_("No calling method enabled"), _("Please enable at least one in the settings."))
        show_settings()
        return None
    if len(modes) == 1:
        mode = modes[0]
    else:
        mode = ui.choose_method(number, [(m, settings.mode_label(m, s)) for m in modes])
        if mode is None:
            return None
    last_call = f"{number} ({settings.mode_label(mode, s)})"

    if mode == settings.MODE_APP:
        try:
            forward_to_app(url, s["appPath"], on_error)
        except dialer.DialError as e:
            on_error(str(e))
        return last_call

    if mode == settings.MODE_PHONIX:
        originate, secret = dialer.originate_phonix, settings.get_secret(settings.ACCOUNT_PHONIX)
    else:
        originate, secret = dialer.originate_ari, settings.get_secret(settings.ACCOUNT_ARI)

    def run():
        try:
            originate(number, s, secret)
        except dialer.DialError as e:
            on_error(str(e))

    threading.Thread(target=run, daemon=True).start()
    return last_call
