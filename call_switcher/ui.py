import re

from AppKit import (
    NSAlert,
    NSAlertFirstButtonReturn,
    NSAlertStyleWarning,
    NSApp,
    NSMakeRect,
    NSPasteboard,
    NSPasteboardTypeString,
    NSTextField,
)
from .i18n import _


def activate():
    if hasattr(NSApp, "activate"):
        NSApp.activate()
    else:
        NSApp.activateIgnoringOtherApps_(True)


def show_alert(title: str, text: str = ""):
    activate()
    alert = NSAlert.alloc().init()
    alert.setAlertStyle_(NSAlertStyleWarning)
    alert.setMessageText_(title)
    alert.setInformativeText_(text)
    alert.runModal()


def _clipboard_number() -> str:
    text = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString) or ""
    text = str(text).strip()
    return text if re.fullmatch(r"[0-9+*#()/.\s-]{3,30}", text) else ""


def ask_number() -> str | None:
    activate()
    alert = NSAlert.alloc().init()
    alert.setMessageText_(_("Dial Number"))
    alert.addButtonWithTitle_(_("Call"))
    alert.addButtonWithTitle_(_("Cancel"))

    field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 240, 24))
    field.setStringValue_(_clipboard_number())
    field.setPlaceholderString_("+41 44 123 45 67")
    alert.setAccessoryView_(field)
    alert.window().setInitialFirstResponder_(field)

    if alert.runModal() == NSAlertFirstButtonReturn:
        return str(field.stringValue())
    return None


def choose_method(number: str, choices: list[tuple[str, str]]) -> str | None:
    """Ask which method to call with; `choices` are (mode, label). Returns the mode or None."""
    activate()
    alert = NSAlert.alloc().init()
    alert.setMessageText_(_("Call {number}", number=number))
    alert.setInformativeText_(_("How do you want to call?"))
    for _mode, label in choices:
        alert.addButtonWithTitle_(label)
    alert.addButtonWithTitle_(_("Cancel")).setKeyEquivalent_("\x1b")

    index = alert.runModal() - NSAlertFirstButtonReturn
    return choices[index][0] if 0 <= index < len(choices) else None
