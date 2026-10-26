"""macOS backend: settings in NSUserDefaults, secrets in the keychain, phone apps via NSWorkspace."""
import os
import subprocess

from AppKit import NSWorkspace, NSWorkspaceOpenConfiguration
from Foundation import NSURL, NSUserDefaults

from . import settings
from .dialer import DialError
from .i18n import _


def _defaults():
    d = NSUserDefaults.standardUserDefaults()
    d.registerDefaults_(settings.DEFAULTS)
    return d


def load() -> dict:
    d = _defaults()
    return settings.normalize({key: d.objectForKey_(key) for key in settings.DEFAULTS})


def save(values: dict):
    d = _defaults()
    for key, value in values.items():
        if key in settings.DEFAULTS:
            d.setObject_forKey_(value, key)


def get_secret(account: str) -> str:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password",
         "-s", settings.BUNDLE_ID, "-a", account, "-w"],
        capture_output=True, text=True,
    )
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def set_secret(account: str, secret: str):
    if not secret:
        subprocess.run(
            ["/usr/bin/security", "delete-generic-password",
             "-s", settings.BUNDLE_ID, "-a", account],
            capture_output=True,
        )
        return
    subprocess.run(
        ["/usr/bin/security", "add-generic-password", "-U",
         "-s", settings.BUNDLE_ID, "-a", account, "-l", f"Call Switcher {account}",
         "-w", secret],
        capture_output=True, check=True,
    )


def forward_to_app(url: str, app_path: str, on_error):
    """Open the URL explicitly with the given app (no loop through the tel: default)."""
    if not os.path.isdir(app_path):
        raise DialError(_("Phone app not found: {path}", path=app_path))

    def completion(app, error):
        if error is not None:
            on_error(str(error.localizedDescription()))

    NSWorkspace.sharedWorkspace().openURLs_withApplicationAtURL_configuration_completionHandler_(
        [NSURL.URLWithString_(url)],
        NSURL.fileURLWithPath_(app_path),
        NSWorkspaceOpenConfiguration.configuration(),
        completion,
    )
