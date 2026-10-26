from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import settings
from ..i18n import _


class Tray:
    def __init__(self, app, icon: QIcon):
        self.app = app
        self.item = QSystemTrayIcon(QIcon.fromTheme("call-start", icon))
        self.item.setToolTip("Call Switcher")

        menu = QMenu()
        menu.aboutToShow.connect(self._update)
        self.mode_item = menu.addAction("")
        self.mode_item.setEnabled(False)
        self.last_item = menu.addAction("")
        self.last_item.setEnabled(False)
        menu.addSeparator()
        menu.addAction(_("Dial Number…"), app.dial_manually)
        menu.addAction(_("Settings…"), app.show_settings)
        menu.addSeparator()
        menu.addAction(_("Quit Call Switcher"), app.quit)
        self.menu = menu  # QSystemTrayIcon does not take ownership

        self.item.setContextMenu(menu)
        self.item.activated.connect(self._activated)
        self._update()
        self.item.show()

    def _update(self):
        s = settings.load()
        labels = [settings.mode_label(m, s) for m in settings.enabled_modes(s)]
        self.mode_item.setText(_("Active: {methods}", methods=", ".join(labels)) if labels else _("No method enabled"))
        last = self.app.last_call
        self.last_item.setText(_("Last call: {call}", call=last) if last else _("No calls yet"))

    def _activated(self, reason):
        # A left click opens the menu on most desktops already; where it does not, show the settings.
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.app.show_settings()
