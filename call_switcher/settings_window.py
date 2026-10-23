import os
import threading

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBundle,
    NSButton,
    NSControlStateValueOff,
    NSControlStateValueOn,
    NSView,
    NSFileManager,
    NSFont,
    NSGridCell,
    NSGridCellPlacementTrailing,
    NSGridView,
    NSLayoutAttributeLeading,
    NSModalResponseOK,
    NSOpenPanel,
    NSSegmentedControl,
    NSSegmentSwitchTrackingSelectOne,
    NSSecureTextField,
    NSStackView,
    NSStackViewGravityBottom,
    NSStackViewGravityTop,
    NSStackViewGravityTrailing,
    NSTextAlignmentRight,
    NSTextField,
    NSUserInterfaceLayoutOrientationHorizontal,
    NSUserInterfaceLayoutOrientationVertical,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
    NSWorkspace,
)
from Foundation import NSURL, NSMakeRect, NSObject
from PyObjCTools import AppHelper

from . import dialer, settings, ui
from .i18n import _

SMAppServiceStatusEnabled = 1

def _mode_title(mode):
    return {settings.MODE_APP: _("Phone App"), settings.MODE_PHONIX: "PhonixPBX", settings.MODE_ARI: "Asterisk ARI"}[mode]


def _label(text, bold=False):
    label = NSTextField.labelWithString_(text)
    label.setAlignment_(NSTextAlignmentRight)
    if bold:
        label.setFont_(NSFont.boldSystemFontOfSize_(NSFont.systemFontSize()))
    return label


def _field(width, placeholder="", secure=False):
    field = (NSSecureTextField if secure else NSTextField).textFieldWithString_("")
    field.setPlaceholderString_(placeholder)
    field.widthAnchor().constraintEqualToConstant_(width).setActive_(True)
    return field


def _hstack(views):
    stack = NSStackView.stackViewWithViews_(views)
    stack.setOrientation_(NSUserInterfaceLayoutOrientationHorizontal)
    stack.setSpacing_(8)
    return stack


def _is_bundled():
    return NSBundle.mainBundle().bundleIdentifier() == settings.BUNDLE_ID


class SettingsWindowController(NSObject):
    def init(self):
        self = objc.super(SettingsWindowController, self).init()
        if self is None:
            return None
        self._build()
        return self

    # --- layout ---------------------------------------------------------

    @objc.python_method
    def _build(self):
        # The segmented control only picks which method is being edited; each one is enabled on its own.
        self.mode_picker = NSSegmentedControl.segmentedControlWithLabels_trackingMode_target_action_(
            [_mode_title(m) for m in settings.MODES], NSSegmentSwitchTrackingSelectOne, self, "modeChanged:")
        self.enabled = {
            mode: NSButton.checkboxWithTitle_target_action_(
                _("Offer {method} when calling", method=_mode_title(mode)), self, "enabledChanged:")
            for mode in settings.MODES
        }

        self.app_path = _field(260)
        self.app_path.setEditable_(False)
        self.choose_app = NSButton.buttonWithTitle_target_action_(_("Choose…"), self, "chooseApp:")

        self.host = _field(170, "192.168.1.100")
        self.port = _field(60, "8088")
        self.https = NSButton.checkboxWithTitle_target_action_("HTTPS", None, None)
        self.user = _field(260)
        self.password = _field(260, secure=True)
        self.endpoint = _field(260, "PJSIP/100")
        self.context = _field(260, "from-internal")
        self.caller_id = _field(260, _("optional"))
        self.ari_test = NSButton.buttonWithTitle_target_action_(_("Test Connection"), self, "testConnection:")
        self.ari_status = NSTextField.labelWithString_("")

        self.phonix_url = _field(260, "https://pbx.example.com")
        self.phonix_extension = _field(80, "100")
        self.phonix_token = _field(260, "phx_…", secure=True)
        self.phonix_insecure = NSButton.checkboxWithTitle_target_action_(
            _("Don’t verify certificate (self-signed)"), None, None)
        self.phonix_test = NSButton.buttonWithTitle_target_action_(_("Test Connection"), self, "testConnection:")
        self.phonix_status = NSTextField.labelWithString_("")

        self.login_item = NSButton.checkboxWithTitle_target_action_(_("Start at login"), None, None)
        self.handler_label = NSTextField.labelWithString_("")
        self.make_default = NSButton.buttonWithTitle_target_action_(_("Set as Default"), self, "makeDefault:")

        empty = NSGridCell.emptyContentView()
        sections = [
            (None, [
                [_label(_("Method:")), self.mode_picker],
            ]),
            (settings.MODE_APP, [
                [_label(_("Enabled:")), self.enabled[settings.MODE_APP]],
                [_label(_("Phone app:")), _hstack([self.app_path, self.choose_app])],
            ]),
            (settings.MODE_ARI, [
                [_label(_("Enabled:")), self.enabled[settings.MODE_ARI]],
                [_label(_("Host:")), _hstack([self.host, NSTextField.labelWithString_(_("Port:")), self.port, self.https])],
                [_label(_("User:")), self.user],
                [_label(_("Password:")), self.password],
                [_label(_("Endpoint:")), self.endpoint],
                [_label(_("Context:")), self.context],
                [_label(_("Caller ID:")), self.caller_id],
                [empty, _hstack([self.ari_test, self.ari_status])],
            ]),
            (settings.MODE_PHONIX, [
                [_label(_("Enabled:")), self.enabled[settings.MODE_PHONIX]],
                [_label(_("Server URL:")), self.phonix_url],
                [empty, self.phonix_insecure],
                [_label(_("Extension:")), self.phonix_extension],
                [_label(_("API token:")), self.phonix_token],
                [empty, _hstack([self.phonix_test, self.phonix_status])],
            ]),
            (None, [
                [_label(_("General"), bold=True), empty],
                [empty, self.login_item],
                [_label(_("tel: links:")), _hstack([self.handler_label, self.make_default])],
            ]),
        ]
        rows, self.mode_rows = [], {}
        for mode, section_rows in sections:
            if mode is not None:
                self.mode_rows[mode] = range(len(rows), len(rows) + len(section_rows))
            rows.extend(section_rows)
        grid = NSGridView.gridViewWithViews_(rows)
        self.grid = grid
        grid.setRowSpacing_(8)
        grid.setColumnSpacing_(10)
        # Labels of all methods share one column width, so the fields do not move when switching.
        labels = grid.columnAtIndex_(0)
        labels.setWidth_(max(row[0].fittingSize().width for row in rows))
        labels.setXPlacement_(NSGridCellPlacementTrailing)

        cancel = NSButton.buttonWithTitle_target_action_(_("Cancel"), self, "cancel:")
        cancel.setKeyEquivalent_("\x1b")
        save = NSButton.buttonWithTitle_target_action_(_("Save"), self, "save:")
        save.setKeyEquivalent_("\r")
        buttons = _hstack([])
        buttons.setViews_inGravity_([cancel, save], NSStackViewGravityTrailing)

        # Form at the top, buttons at the bottom; a shorter method leaves the space in between.
        content = NSStackView.alloc().init()
        content.setOrientation_(NSUserInterfaceLayoutOrientationVertical)
        content.setAlignment_(NSLayoutAttributeLeading)
        content.setSpacing_(20)
        content.setViews_inGravity_([grid], NSStackViewGravityTop)
        content.setViews_inGravity_([buttons], NSStackViewGravityBottom)
        buttons.widthAnchor().constraintEqualToAnchor_(content.widthAnchor()).setActive_(True)
        content.setTranslatesAutoresizingMaskIntoConstraints_(False)

        # Pin the stack with explicit margins; NSStackView edge insets are not reliable as window content.
        self.container = container = NSView.alloc().init()
        container.addSubview_(content)
        margin = 20
        for constraint in [
            content.topAnchor().constraintEqualToAnchor_constant_(container.topAnchor(), margin),
            content.leadingAnchor().constraintEqualToAnchor_constant_(container.leadingAnchor(), margin),
            container.trailingAnchor().constraintEqualToAnchor_constant_(content.trailingAnchor(), margin),
            container.bottomAnchor().constraintEqualToAnchor_constant_(content.bottomAnchor(), margin),
        ]:
            constraint.setActive_(True)

        # Fixed window size: large enough for the biggest method in the current language.
        sizes = []
        for mode in settings.MODES:
            self._show_rows_of(mode)
            container.layoutSubtreeIfNeeded()
            sizes.append(container.fittingSize())
        container.widthAnchor().constraintEqualToConstant_(max(size.width for size in sizes)).setActive_(True)
        container.heightAnchor().constraintEqualToConstant_(max(size.height for size in sizes)).setActive_(True)

        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 520, 480),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_(_("Call Switcher – Settings"))
        self.window.setReleasedWhenClosed_(False)
        self.window.setContentView_(container)
        self.window.setContentSize_(container.fittingSize())

    # --- state ----------------------------------------------------------

    @objc.python_method
    def show(self):
        s = settings.load()
        for mode, checkbox in self.enabled.items():
            checkbox.setState_(NSControlStateValueOn if s[settings.ENABLED_KEYS[mode]] else NSControlStateValueOff)
        first = (settings.enabled_modes(s) or [settings.MODE_APP])[0]
        self.mode_picker.setSelectedSegment_(settings.MODES.index(first))
        self.app_path.setStringValue_(s["appPath"])
        self.host.setStringValue_(s["ariHost"])
        self.port.setStringValue_(str(s["ariPort"]))
        self.https.setState_(NSControlStateValueOn if s["ariHTTPS"] else NSControlStateValueOff)
        self.user.setStringValue_(s["ariUser"])
        self.password.setStringValue_(settings.get_secret(settings.ACCOUNT_ARI))
        self.endpoint.setStringValue_(s["ariEndpoint"])
        self.context.setStringValue_(s["ariContext"])
        self.caller_id.setStringValue_(s["ariCallerId"])
        self.ari_status.setStringValue_("")
        self.phonix_url.setStringValue_(s["phonixURL"])
        self.phonix_insecure.setState_(NSControlStateValueOn if s["phonixInsecure"] else NSControlStateValueOff)
        self.phonix_extension.setStringValue_(s["phonixExtension"])
        self.phonix_token.setStringValue_(settings.get_secret(settings.ACCOUNT_PHONIX))
        self.phonix_status.setStringValue_("")

        self.login_item.setEnabled_(_is_bundled())
        self.login_item.setState_(NSControlStateValueOn if self._login_item_enabled() else NSControlStateValueOff)
        self._refresh_handler_label()
        self._refresh_segment_labels()
        self._update_visible_rows()

        self.window.center()
        ui.activate()
        self.window.makeKeyAndOrderFront_(None)

    @objc.python_method
    def _form_values(self) -> dict:
        try:
            port = int(str(self.port.stringValue()).strip() or 8088)
        except ValueError:
            port = 8088
        return {
            **{settings.ENABLED_KEYS[m]: c.state() == NSControlStateValueOn for m, c in self.enabled.items()},
            "appPath": str(self.app_path.stringValue()),
            "ariHost": str(self.host.stringValue()).strip(),
            "ariPort": port,
            "ariHTTPS": self.https.state() == NSControlStateValueOn,
            "ariUser": str(self.user.stringValue()).strip(),
            "ariEndpoint": str(self.endpoint.stringValue()).strip(),
            "ariContext": str(self.context.stringValue()).strip(),
            "ariCallerId": str(self.caller_id.stringValue()).strip(),
            "phonixURL": str(self.phonix_url.stringValue()).strip(),
            "phonixExtension": str(self.phonix_extension.stringValue()).strip(),
            "phonixInsecure": self.phonix_insecure.state() == NSControlStateValueOn,
        }

    @objc.python_method
    def _selected_mode(self) -> str:
        return settings.MODES[max(self.mode_picker.selectedSegment(), 0)]

    @objc.python_method
    def _refresh_segment_labels(self):
        for i, mode in enumerate(settings.MODES):
            mark = "✓ " if self.enabled[mode].state() == NSControlStateValueOn else ""
            self.mode_picker.setLabel_forSegment_(mark + _mode_title(mode), i)

    @objc.python_method
    def _update_visible_rows(self):
        self._show_rows_of(self._selected_mode())

    @objc.python_method
    def _show_rows_of(self, selected):
        for mode, indexes in self.mode_rows.items():
            for i in indexes:
                self.grid.rowAtIndex_(i).setHidden_(mode != selected)

    @objc.python_method
    def _refresh_handler_label(self):
        app_url = NSWorkspace.sharedWorkspace().URLForApplicationToOpenURL_(NSURL.URLWithString_("tel:1"))
        if app_url is None:
            name = _("no app")
        else:
            name = NSFileManager.defaultManager().displayNameAtPath_(app_url.path())
        self.handler_label.setStringValue_(_("opens with: {app}", app=name))

    # --- login item -----------------------------------------------------

    @objc.python_method
    def _login_item_enabled(self):
        if not _is_bundled():
            return False
        from ServiceManagement import SMAppService
        return SMAppService.mainAppService().status() == SMAppServiceStatusEnabled

    @objc.python_method
    def _apply_login_item(self, enabled):
        if not _is_bundled() or enabled == self._login_item_enabled():
            return
        from ServiceManagement import SMAppService
        service = SMAppService.mainAppService()
        if enabled:
            ok, error = service.registerAndReturnError_(None)
        else:
            ok, error = service.unregisterAndReturnError_(None)
        if not ok:
            ui.show_alert(_("Could not change login item"), str(error.localizedDescription()))

    # --- actions --------------------------------------------------------

    def modeChanged_(self, sender):
        self._update_visible_rows()

    def enabledChanged_(self, sender):
        self._refresh_segment_labels()

    def chooseApp_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setTitle_(_("Choose Phone App"))
        panel.setAllowedFileTypes_(["app"])
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setDirectoryURL_(NSURL.fileURLWithPath_("/Applications"))
        if panel.runModal() == NSModalResponseOK:
            self.app_path.setStringValue_(panel.URL().path())

    def testConnection_(self, sender):
        values = self._form_values()
        if sender == self.phonix_test:
            test, secret, status = dialer.test_phonix, str(self.phonix_token.stringValue()), self.phonix_status
        else:
            test, secret, status = dialer.test_ari, str(self.password.stringValue()), self.ari_status
        status.setStringValue_(_("Testing…"))

        def run():
            try:
                message = test(values, secret)
            except dialer.DialError as e:
                message = f"❌ {e}"
            else:
                message = f"✅ {message}"
            AppHelper.callAfter(status.setStringValue_, message)

        threading.Thread(target=run, daemon=True).start()

    def makeDefault_(self, sender):
        if not _is_bundled():
            ui.show_alert(_("Only possible in the built app"),
                          _("Start “Call Switcher.app” to make it the default for tel: links."))
            return
        bundle_url = NSBundle.mainBundle().bundleURL()

        def done(error):
            if error is not None:
                AppHelper.callAfter(ui.show_alert, _("Could not set the default"),
                                    str(error.localizedDescription()))
            AppHelper.callAfter(self._refresh_handler_label)

        for scheme in dialer.SCHEMES:
            NSWorkspace.sharedWorkspace().setDefaultApplicationAtURL_toOpenURLsWithScheme_completionHandler_(
                bundle_url, scheme, done)

    def save_(self, sender):
        values = self._form_values()
        if not settings.enabled_modes(values):
            ui.show_alert(_("No method enabled."), _("Please enable at least one calling method."))
            return
        if values["appEnabled"] and not os.path.isdir(values["appPath"]):
            ui.show_alert(_("No phone app selected"), _("Please choose a valid .app."))
            return
        if values["phonixEnabled"] and not values["phonixExtension"]:
            ui.show_alert(_("No extension entered"), _("Please enter the extension of your own phone."))
            return
        settings.save(values)
        try:
            settings.set_secret(settings.ACCOUNT_ARI, str(self.password.stringValue()))
            settings.set_secret(settings.ACCOUNT_PHONIX, str(self.phonix_token.stringValue()).strip())
        except Exception as e:
            ui.show_alert(_("Could not save the credentials in the keychain"), str(e))
            return
        self._apply_login_item(self.login_item.state() == NSControlStateValueOn)
        self.window.close()

    def cancel_(self, sender):
        self.window.close()
