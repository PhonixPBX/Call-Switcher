import threading

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from .. import dialer, settings
from ..i18n import _
from . import host, store, ui


def _mode_title(mode):
    return {settings.MODE_APP: _("Phone App"), settings.MODE_PHONIX: "PhonixPBX", settings.MODE_ARI: "Asterisk ARI"}[mode]


def _field(width, placeholder="", secure=False):
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setFixedWidth(width)
    if secure:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


def _plain_label():
    """For text from outside (server errors, app names), which must not be read as HTML."""
    label = QLabel()
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


def _hbox(*widgets):
    box = QWidget()
    layout = QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch()
    return box


class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Call Switcher – Settings"))
        self.apps = []
        self._build()

    # --- layout ---------------------------------------------------------

    def _build(self):
        # The tab bar only picks which method is being edited; each one is enabled on its own.
        self.mode_picker = QTabBar()
        for mode in settings.MODES:
            self.mode_picker.addTab(_mode_title(mode))
        self.mode_picker.setExpanding(False)
        self.enabled = {}
        for mode in settings.MODES:
            checkbox = QCheckBox(_("Offer {method} when calling", method=_mode_title(mode)))
            checkbox.toggled.connect(self._refresh_tab_labels)
            self.enabled[mode] = checkbox

        self.app = QComboBox()
        self.app.setMinimumWidth(260)
        self.app.setPlaceholderText(_("No phone app found"))

        self.host = _field(170, "192.168.1.100")
        self.port = _field(60, "8088")
        self.https = QCheckBox("HTTPS")
        self.user = _field(260)
        self.password = _field(260, secure=True)
        self.endpoint = _field(260, "PJSIP/100")
        self.context = _field(260, "from-internal")
        self.caller_id = _field(260, _("optional"))
        self.ari_test = QPushButton(_("Test Connection"))
        self.ari_test.clicked.connect(lambda: self._test_connection(settings.MODE_ARI))
        self.ari_status = _plain_label()

        self.phonix_url = _field(260, "https://pbx.example.com")
        self.phonix_extension = _field(80, "100")
        self.phonix_token = _field(260, "phx_…", secure=True)
        self.phonix_insecure = QCheckBox(_("Don’t verify certificate (self-signed)"))
        self.phonix_test = QPushButton(_("Test Connection"))
        self.phonix_test.clicked.connect(lambda: self._test_connection(settings.MODE_PHONIX))
        self.phonix_status = _plain_label()

        self.login_item = QCheckBox(_("Start at login"))
        self.handler_label = _plain_label()
        self.make_default = QPushButton(_("Set as Default"))
        self.make_default.clicked.connect(self._make_default)

        pages = {
            settings.MODE_APP: [
                (_("Enabled:"), self.enabled[settings.MODE_APP]),
                (_("Phone app:"), self.app),
            ],
            settings.MODE_ARI: [
                (_("Enabled:"), self.enabled[settings.MODE_ARI]),
                (_("Host:"), _hbox(self.host, QLabel(_("Port:")), self.port, self.https)),
                (_("User:"), self.user),
                (_("Password:"), self.password),
                (_("Endpoint:"), self.endpoint),
                (_("Context:"), self.context),
                (_("Caller ID:"), self.caller_id),
                ("", _hbox(self.ari_test, self.ari_status)),
            ],
            settings.MODE_PHONIX: [
                (_("Enabled:"), self.enabled[settings.MODE_PHONIX]),
                (_("Server URL:"), self.phonix_url),
                ("", self.phonix_insecure),
                (_("Extension:"), self.phonix_extension),
                (_("API token:"), self.phonix_token),
                ("", _hbox(self.phonix_test, self.phonix_status)),
            ],
        }
        general = QLabel(_("General"))
        bold = QFont(general.font())
        bold.setBold(True)
        general.setFont(bold)
        general_rows = [
            (general, None),
            ("", self.login_item),
            (_("tel: links:"), _hbox(self.handler_label, self.make_default)),
        ]

        # Labels of all methods share one width, so the fields do not move when switching.
        labels = []

        def form(rows):
            layout = QFormLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setVerticalSpacing(8)
            layout.setHorizontalSpacing(10)
            layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
            for label, field in rows:
                label = label if isinstance(label, QLabel) else QLabel(label)
                label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                labels.append(label)
                if field is None:
                    layout.addRow(label)
                else:
                    layout.addRow(label, field)
            return layout

        self.pages = QStackedWidget()  # as large as its largest page, so the window keeps its size
        for mode in settings.MODES:
            page = QWidget()
            page.setLayout(form(pages[mode]))
            self.pages.addWidget(page)
        self.mode_picker.currentChanged.connect(self.pages.setCurrentIndex)
        header = form([(_("Method:"), self.mode_picker)])
        footer = form(general_rows)
        general.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        width = max(label.sizeHint().width() for label in labels if label is not general)
        for label in labels:
            if label is not general:
                label.setFixedWidth(width)

        cancel = QPushButton(_("Cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(_("Save"))
        save.setDefault(True)
        save.clicked.connect(self._save)

        content = QVBoxLayout(self)
        content.setContentsMargins(20, 20, 20, 20)
        content.setSpacing(20)
        content.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        content.addLayout(header)
        content.addWidget(self.pages)
        content.addLayout(footer)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        content.addLayout(buttons)

    # --- state ----------------------------------------------------------

    def show_settings(self):
        s = settings.load()
        for mode, checkbox in self.enabled.items():
            checkbox.setChecked(s[settings.ENABLED_KEYS[mode]])
        first = (settings.enabled_modes(s) or [settings.MODE_APP])[0]
        self.mode_picker.setCurrentIndex(settings.MODES.index(first))
        self._fill_apps(s["appPath"], s["appName"])
        self.host.setText(s["ariHost"])
        self.port.setText(str(s["ariPort"]))
        self.https.setChecked(s["ariHTTPS"])
        self.user.setText(s["ariUser"])
        self.password.setText(settings.get_secret(settings.ACCOUNT_ARI))
        self.endpoint.setText(s["ariEndpoint"])
        self.context.setText(s["ariContext"])
        self.caller_id.setText(s["ariCallerId"])
        self.ari_status.setText("")
        self.phonix_url.setText(s["phonixURL"])
        self.phonix_insecure.setChecked(s["phonixInsecure"])
        self.phonix_extension.setText(s["phonixExtension"])
        self.phonix_token.setText(settings.get_secret(settings.ACCOUNT_PHONIX))
        self.phonix_status.setText("")

        self.login_item.setEnabled(host.installed())
        self.login_item.setChecked(host.installed() and s.get("loginItem", False))
        self._refresh_handler_label()
        self._refresh_tab_labels()

        self.show()
        self.raise_()
        self.activateWindow()

    def _fill_apps(self, path, name):
        self.app.clear()
        self.apps = host.list_phone_apps()
        for app_path, app_name in self.apps:
            self.app.addItem(app_name, app_path)
        if path and self.app.findData(path) < 0:  # keep a chosen app that is no longer found
            self.app.addItem(name or host.app_id(path), path)
        self.app.setCurrentIndex(self.app.findData(path) if path else (0 if self.app.count() else -1))

    def _form_values(self) -> dict:
        try:
            port = int(self.port.text().strip() or 8088)
        except ValueError:
            port = 8088
        return {
            **{settings.ENABLED_KEYS[m]: c.isChecked() for m, c in self.enabled.items()},
            "appPath": self.app.currentData() or "",
            "appName": self.app.currentText() if self.app.currentIndex() >= 0 else "",
            "ariHost": self.host.text().strip(),
            "ariPort": port,
            "ariHTTPS": self.https.isChecked(),
            "ariUser": self.user.text().strip(),
            "ariEndpoint": self.endpoint.text().strip(),
            "ariContext": self.context.text().strip(),
            "ariCallerId": self.caller_id.text().strip(),
            "phonixURL": self.phonix_url.text().strip(),
            "phonixExtension": self.phonix_extension.text().strip(),
            "phonixInsecure": self.phonix_insecure.isChecked(),
        }

    def _selected_mode(self) -> str:
        return settings.MODES[max(self.mode_picker.currentIndex(), 0)]

    def _refresh_tab_labels(self):
        for i, mode in enumerate(settings.MODES):
            mark = "✓ " if self.enabled[mode].isChecked() else ""
            self.mode_picker.setTabText(i, mark + _mode_title(mode))

    def _refresh_handler_label(self):
        handler = host.default_handler()
        if not handler:
            name = _("no app")
        elif handler == host.OWN_ID:
            name = "Call Switcher"
        else:
            names = {host.app_id(path): app_name for path, app_name in self.apps}
            name = names.get(handler, handler.removesuffix(".desktop"))
        self.handler_label.setText(_("opens with: {app}", app=name))

    # --- actions --------------------------------------------------------

    def _test_connection(self, mode):
        values = self._form_values()
        if mode == settings.MODE_PHONIX:
            test, secret, status = dialer.test_phonix, self.phonix_token.text(), self.phonix_status
        else:
            test, secret, status = dialer.test_ari, self.password.text(), self.ari_status
        status.setText(_("Testing…"))

        def run():
            try:
                message = test(values, secret)
            except dialer.DialError as e:
                message = f"❌ {e}"
            else:
                message = f"✅ {message}"
            ui.call_after(status.setText, message)

        threading.Thread(target=run, daemon=True).start()

    def _make_default(self):
        if not host.installed():
            ui.show_alert(_("Only possible in the built app"), host.install_hint())
            return
        try:
            host.set_default()
        except host.HostError as e:
            ui.show_alert(_("Could not set the default"), str(e))
        self._refresh_handler_label()

    def _apply_login_item(self, enabled):
        if not host.installed() or enabled == store.load()["loginItem"]:
            return

        def run():
            try:
                host.request_autostart(enabled)
            except host.HostError as e:
                ui.call_after(ui.show_alert, _("Could not change login item"), str(e))
            else:
                store.save({"loginItem": enabled})

        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        values = self._form_values()
        if not settings.enabled_modes(values):
            ui.show_alert(_("No method enabled."), _("Please enable at least one calling method."))
            return
        if values["appEnabled"] and not values["appPath"]:
            ui.show_alert(_("No phone app selected"), _("Please choose a phone app."))
            return
        if values["phonixEnabled"] and not values["phonixExtension"]:
            ui.show_alert(_("No extension entered"), _("Please enter the extension of your own phone."))
            return
        settings.save(values)
        try:
            settings.set_secret(settings.ACCOUNT_ARI, self.password.text())
            settings.set_secret(settings.ACCOUNT_PHONIX, self.phonix_token.text().strip())
        except Exception as e:
            ui.show_alert(_("Could not save the credentials in the keyring"), str(e))
            return
        self._apply_login_item(self.login_item.isChecked())
        self.accept()
