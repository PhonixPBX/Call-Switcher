"""Linux part of the Qt app. Everything that has to happen on the host system rather than
inside the Flatpak sandbox: listing and starting phone apps, the default handler for tel:
links, and autostart.

Inside the Flatpak, commands run through `flatpak-spawn --host`; in a development checkout
they run directly. Paths of .desktop files are always host paths.
"""
import os
import random
import subprocess
import threading

from .. import settings
from ..dialer import SCHEMES, DialError
from ..i18n import _

__all__ = ["OWN_ID", "HostError", "installed", "install_hint", "app_id", "list_phone_apps",
           "forward_to_app", "default_handler", "set_default", "request_autostart"]

DESKTOP_ID = OWN_ID = f"{settings.BUNDLE_ID}.desktop"

# Prints "path<TAB>name" for every visible .desktop file that handles sip:, tel: or callto:,
# in XDG order (user dir first). Only needs sh, find, grep and cut, which every host has.
_LIST_APPS = r"""
IFS=:
for dir in "${XDG_DATA_HOME:-$HOME/.local/share}" ${XDG_DATA_DIRS:-/usr/local/share:/usr/share}; do
    [ -d "$dir/applications" ] || continue
    find -L "$dir/applications" -name '*.desktop' -exec \
        grep -lE '^MimeType=(.*;)?x-scheme-handler/(sip|tel|callto)(;|$)' {} + 2>/dev/null
done | while IFS= read -r file; do
    grep -qE '^(NoDisplay|Hidden)=true' "$file" && continue
    printf '%s\t%s\n' "$file" "$(grep -m1 '^Name=' "$file" | cut -d= -f2-)"
done
"""


class HostError(Exception):
    pass


def in_flatpak() -> bool:
    return os.path.exists("/.flatpak-info")


def installed() -> bool:
    """Runs as the Flatpak, not from a checkout (default handler and autostart need that)."""
    return in_flatpak()


def install_hint() -> str:
    return _("Install the Flatpak to make Call Switcher the default for tel: links.")


def host(cmd: list[str]) -> list[str]:
    return ["flatpak-spawn", "--host", *cmd] if in_flatpak() else cmd


def _run(cmd: list[str], timeout: float = 10) -> str:
    try:
        result = subprocess.run(host(cmd), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise HostError(str(e)) from e
    if result.returncode != 0:
        raise HostError(result.stderr.strip() or f"{cmd[0]} exited with {result.returncode}")
    return result.stdout


def desktop_id(path: str) -> str:
    """'/usr/share/applications/kde/org.x.desktop' -> 'kde-org.x.desktop' (XDG desktop file ID)."""
    rel = path.split("/applications/", 1)[-1]
    return rel.replace("/", "-")


app_id = desktop_id


def list_phone_apps() -> list[tuple[str, str]]:
    """(path, name) of the installed apps that handle sip:/tel:/callto:, without Call Switcher."""
    try:
        output = _run(["sh", "-c", _LIST_APPS])
    except HostError:
        return []
    apps, seen = [], {DESKTOP_ID}
    for line in output.splitlines():
        path, _sep, name = line.partition("\t")
        app_id = desktop_id(path)
        if app_id in seen:  # an earlier directory overrides later ones
            continue
        seen.add(app_id)
        apps.append((path, name or app_id.removesuffix(".desktop")))
    return sorted(apps, key=lambda app: app[1].casefold())


def forward_to_app(url: str, app_path: str, on_error):
    """Open the URL with the given .desktop file (no loop through the tel: default)."""
    if not app_path:
        raise DialError(_("No phone app selected"))

    def run():
        try:
            _run(["gio", "launch", app_path, url], timeout=30)
        except HostError as e:
            on_error(_("Could not start the phone app: {error}", error=e))

    threading.Thread(target=run, daemon=True).start()


def default_handler() -> str:
    """Desktop file ID that opens tel: links, or '' if there is none."""
    try:
        return _run(["xdg-mime", "query", "default", "x-scheme-handler/tel"]).strip()
    except HostError:
        return ""


def set_default():
    _run(["xdg-mime", "default", DESKTOP_ID, *(f"x-scheme-handler/{scheme}" for scheme in SCHEMES)])


def request_autostart(enabled: bool, timeout: float = 120):
    """Ask the Background portal to (not) start the Flatpak at login. Blocks until the user answered."""
    from jeepney import DBusAddress, MatchRule, new_method_call
    from jeepney.bus_messages import message_bus
    from jeepney.io.blocking import open_dbus_connection

    portal = DBusAddress("/org/freedesktop/portal/desktop", bus_name="org.freedesktop.portal.Desktop",
                         interface="org.freedesktop.portal.Background")
    token = f"callswitcher{random.randrange(1 << 32)}"
    options = {
        "handle_token": ("s", token),
        "reason": ("s", _("Start Call Switcher at login")),
        "autostart": ("b", enabled),
        "commandline": ("as", ["call-switcher", "--background"]),
    }
    try:
        with open_dbus_connection(bus="SESSION") as conn:
            # Subscribe before calling, so the answer cannot arrive before we listen for it.
            sender = conn.unique_name.removeprefix(":").replace(".", "_")
            rule = MatchRule(type="signal", interface="org.freedesktop.portal.Request", member="Response",
                             path=f"/org/freedesktop/portal/desktop/request/{sender}/{token}")
            conn.send_and_get_reply(message_bus.AddMatch(rule))
            with conn.filter(rule) as responses:
                conn.send_and_get_reply(new_method_call(portal, "RequestBackground", "sa{sv}", ("", options)))
                code, results = conn.recv_until_filtered(responses, timeout=timeout).body
    except Exception as e:  # D-Bus errors, no portal, timeout
        raise HostError(str(e)) from e
    if code != 0:
        raise HostError(_("Not allowed in the system settings."))
    if enabled and not results.get("autostart", ("b", False))[1]:
        raise HostError(_("Not allowed in the system settings."))
