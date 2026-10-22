from AppKit import (
    NSImage,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject

from . import settings
from .i18n import _


class MenuBar(NSObject):
    def initWithDelegate_(self, app_delegate):
        self = self.init()
        if self is None:
            return None
        self.app_delegate = app_delegate

        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("phone.fill", "Call Switcher")
        image.setTemplate_(True)
        self.item.button().setImage_(image)

        menu = NSMenu.alloc().init()
        menu.setDelegate_(self)
        menu.setAutoenablesItems_(False)

        self.mode_item = menu.addItemWithTitle_action_keyEquivalent_("", None, "")
        self.mode_item.setEnabled_(False)
        self.last_item = menu.addItemWithTitle_action_keyEquivalent_("", None, "")
        self.last_item.setEnabled_(False)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItemWithTitle_action_keyEquivalent_(_("Dial Number…"), "dial:", "d").setTarget_(self)
        menu.addItemWithTitle_action_keyEquivalent_(_("Settings…"), "openSettings:", ",").setTarget_(self)
        menu.addItem_(NSMenuItem.separatorItem())
        menu.addItemWithTitle_action_keyEquivalent_(_("Quit Call Switcher"), "terminate:", "q")

        self.item.setMenu_(menu)
        return self

    def menuNeedsUpdate_(self, menu):
        s = settings.load()
        labels = [settings.mode_label(m, s) for m in settings.enabled_modes(s)]
        self.mode_item.setTitle_(_("Active: {methods}", methods=", ".join(labels)) if labels else _("No method enabled"))
        last = self.app_delegate.last_call
        self.last_item.setTitle_(_("Last call: {call}", call=last) if last else _("No calls yet"))

    def dial_(self, sender):
        self.app_delegate.dialManually()

    def openSettings_(self, sender):
        self.app_delegate.showSettings()
