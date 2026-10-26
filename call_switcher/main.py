import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
)
from Foundation import NSAppleEventManager, NSObject
from PyObjCTools import AppHelper

from . import calls, macos, ui
from .menubar import MenuBar
from .settings_window import SettingsWindowController
from .i18n import _


def _fourcc(code: bytes) -> int:
    return int.from_bytes(code, "big")


kInternetEventClass = kAEGetURL = _fourcc(b"GURL")
keyDirectObject = _fourcc(b"----")


def _install_edit_menu(app):
    """Accessory apps have no visible menu bar, but Cmd+C/V/X/A only work via the main menu."""
    main_menu = NSMenu.alloc().init()
    edit_item = main_menu.addItemWithTitle_action_keyEquivalent_(_("Edit"), None, "")
    edit_menu = NSMenu.alloc().initWithTitle_(_("Edit"))
    for title, action, key in [
        (_("Undo"), "undo:", "z"),
        (_("Cut"), "cut:", "x"),
        (_("Copy"), "copy:", "c"),
        (_("Paste"), "paste:", "v"),
        (_("Select All"), "selectAll:", "a"),
    ]:
        edit_menu.addItem_(NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key))
    edit_item.setSubmenu_(edit_menu)
    app.setMainMenu_(main_menu)


class AppDelegate(NSObject):
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.last_call = None
        self.menubar = None
        self.settings_window = None
        return self

    def applicationWillFinishLaunching_(self, notification):
        # Register before launch finishes so the URL that launched us is not lost.
        NSAppleEventManager.sharedAppleEventManager().setEventHandler_andSelector_forEventClass_andEventID_(
            self, "handleGetURLEvent:withReplyEvent:", kInternetEventClass, kAEGetURL)

    def applicationDidFinishLaunching_(self, notification):
        _install_edit_menu(NSApplication.sharedApplication())
        self.menubar = MenuBar.alloc().initWithDelegate_(self)

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, has_visible):
        self.showSettings()
        return True

    @objc.typedSelector(b"v@:@@")
    def handleGetURLEvent_withReplyEvent_(self, event, reply):
        url = event.paramDescriptorForKeyword_(keyDirectObject).stringValue()
        if url:
            self.dial(str(url))

    @objc.python_method
    def showSettings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindowController.alloc().init()
        self.settings_window.show()

    @objc.python_method
    def dialManually(self):
        number = ui.ask_number()
        if number:
            self.dial(f"tel:{number}")

    @objc.python_method
    def dial(self, url: str):
        last_call = calls.place_call(url, ui, macos.forward_to_app, self.showSettings, self._on_dial_error)
        if last_call:
            self.last_call = last_call

    @objc.python_method
    def _on_dial_error(self, message: str):
        AppHelper.callAfter(ui.show_alert, _("Call failed"), message)


def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
