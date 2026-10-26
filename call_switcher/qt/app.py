"""Linux and Windows app: a tray icon (where the desktop has one) and a handler for tel:/callto:/sip: links.

`call-switcher URL` dials, `call-switcher` shows the settings, `call-switcher --background`
(autostart) only shows the tray icon. Only one instance runs; later starts hand their URL to it.
"""
import argparse
import os
import pathlib
import secrets
import stat
import sys
import tempfile
import threading

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .. import calls, settings
from ..i18n import _
from . import host, ui
from .settings_dialog import SettingsDialog
from .tray import Tray

SHOW_SETTINGS = "settings"
DIAL = "dial "
ICON = pathlib.Path(__file__).parents[2] / "assets" / "icon.png"  # development checkout


def _private_dir() -> str:
    """A directory in /tmp only we can access, for systems without XDG_RUNTIME_DIR."""
    path = os.path.join(tempfile.gettempdir(), f"call-switcher-{os.getuid()}")
    os.makedirs(path, mode=0o700, exist_ok=True)
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise SystemExit(f"{path} belongs to someone else or is accessible by others")
    return path


def pipe_name(directory: pathlib.Path) -> str:
    """Windows: named pipes are visible to all users of the machine, so their name is not
    guessable: it ends in a random token kept in the user's profile, which others cannot read."""
    path = directory / "instance-token"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x") as f:  # exclusive, so two first starts agree on one token
            f.write(secrets.token_hex(16))
    except FileExistsError:
        pass
    return f"{settings.BUNDLE_ID}-{path.read_text().strip()}"


def socket_path() -> str:
    if sys.platform == "win32":
        return pipe_name(pathlib.Path(os.environ["LOCALAPPDATA"]) / "Call Switcher")
    # XDG_RUNTIME_DIR is private to the user (0700), unlike /tmp.
    runtime = os.environ.get("XDG_RUNTIME_DIR") or _private_dir()
    if os.path.exists("/.flatpak-info"):
        # Shared by all instances of the Flatpak.
        return os.path.join(runtime, "app", settings.BUNDLE_ID, "instance.sock")
    return os.path.join(runtime, f"{settings.BUNDLE_ID}.sock")


def send_to_running(message: str) -> bool:
    """Hand the message to an instance that is already running. False if there is none."""
    sock = QLocalSocket()
    sock.connectToServer(socket_path())
    if not sock.waitForConnected(500):
        return False
    sock.write(f"{message}\n".encode())
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    return True


class App:
    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.last_call = None
        self.settings_dialog = None

        self.server = QLocalServer()
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        QLocalServer.removeServer(socket_path())  # left over from a crash; no other instance answered
        if not self.server.listen(socket_path()):
            ui.show_alert(_("Could not start Call Switcher"), self.server.errorString())
            raise SystemExit(1)

        # Dialogs come and go while a call is placed in the background, so closing the last
        # window must not quit. Without a tray icon the app quits once it is idle instead.
        qapp.setQuitOnLastWindowClosed(False)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(self, qapp.windowIcon())
        else:
            self.idle_timer = QTimer()
            self.idle_timer.timeout.connect(self._quit_if_idle)
            self.idle_timer.start(500)

    def _accept(self):
        while (sock := self.server.nextPendingConnection()) is not None:
            buffer = bytearray()
            sock.readyRead.connect(lambda sock=sock, buffer=buffer: buffer.extend(sock.readAll().data()))

            def received(sock=sock, buffer=buffer):
                buffer.extend(sock.readAll().data())
                sock.deleteLater()
                for line in buffer.decode(errors="replace").splitlines():
                    self.handle(line)

            sock.disconnected.connect(received)

    def _quit_if_idle(self):
        windows = any(w.isVisible() for w in self.qapp.topLevelWidgets())
        if not windows and threading.active_count() == 1:
            self.quit()

    def handle(self, message: str):
        if message.startswith(DIAL):
            self.dial(message.removeprefix(DIAL))
        elif message == SHOW_SETTINGS:
            self.show_settings()

    def show_settings(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog()
        self.settings_dialog.show_settings()

    def dial_manually(self):
        number = ui.ask_number()
        if number:
            self.dial(f"tel:{number}")

    def dial(self, url: str):
        last_call = calls.place_call(url, ui, host.forward_to_app, self.show_settings, self._on_dial_error)
        if last_call:
            self.last_call = last_call

    def _on_dial_error(self, message: str):
        ui.call_after(ui.show_alert, _("Call failed"), message)

    def quit(self):
        self.server.close()
        self.qapp.quit()


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(prog="call-switcher")
    parser.add_argument("--background", action="store_true", help="only show the tray icon (autostart)")
    parser.add_argument("url", nargs="?", help="tel:, callto: or sip: URL to dial")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    qapp = QApplication(sys.argv[:1])
    qapp.setApplicationName("Call Switcher")
    qapp.setDesktopFileName(settings.BUNDLE_ID)  # Wayland matches windows to the .desktop file by this
    qapp.setWindowIcon(QIcon.fromTheme(settings.BUNDLE_ID, QIcon(str(ICON))))

    message = DIAL + args.url if args.url else None if args.background else SHOW_SETTINGS
    if send_to_running(message or ""):
        return

    app = App(qapp)
    if message:
        QTimer.singleShot(0, lambda: app.handle(message))
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
