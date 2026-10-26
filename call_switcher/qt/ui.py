from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from ..calls import clipboard_number
from ..i18n import _


class _Invoker(QObject):
    """Lives in the main thread; a signal emitted from another thread runs the function there."""
    called = Signal(object)

    def __init__(self):
        super().__init__()
        self.called.connect(self._run)

    @Slot(object)
    def _run(self, fn):
        fn()


_invoker = _Invoker()  # created on import, which happens in the main thread


def call_after(fn, *args):
    """Run fn(*args) in the main thread (like AppHelper.callAfter on macOS)."""
    _invoker.called.emit(lambda: fn(*args))


def _message_box(icon, title: str, text: str) -> QMessageBox:
    # The texts can come from a tel: link or a server, so they must not be read as HTML.
    box = QMessageBox(icon, "Call Switcher", "")
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setText(title)
    box.setInformativeText(text)
    return box


def show_alert(title: str, text: str = ""):
    box = _message_box(QMessageBox.Icon.Warning, title, text)
    box.exec()


def ask_number() -> str | None:
    dialog = QInputDialog()
    dialog.setWindowTitle(_("Dial Number"))
    dialog.setLabelText(_("Dial Number"))
    dialog.setOkButtonText(_("Call"))
    dialog.setCancelButtonText(_("Cancel"))
    dialog.setTextValue(clipboard_number(QGuiApplication.clipboard().text()))
    dialog.findChild(QLineEdit).setPlaceholderText("+41 44 123 45 67")
    if dialog.exec():
        return dialog.textValue()
    return None


def choose_method(number: str, choices: list[tuple[str, str]]) -> str | None:
    """Ask which method to call with; `choices` are (mode, label). Returns the mode or None."""
    box = _message_box(QMessageBox.Icon.Question, _("Call {number}", number=number), _("How do you want to call?"))
    buttons = {box.addButton(label, QMessageBox.ButtonRole.AcceptRole): mode for mode, label in choices}
    box.setEscapeButton(box.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole))
    box.exec()
    return buttons.get(box.clickedButton())
