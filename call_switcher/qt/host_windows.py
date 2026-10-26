"""Windows part of the Qt app: phone apps, the default handler for tel: links and autostart,
all in the registry.

The installer (packaging/windows/CallSwitcher.iss) registers Call Switcher as ProgID
CallSwitcher.URL with the capabilities for tel:, callto: and sip:. Since Windows 10, apps may
not make themselves the default, so "Set as Default" opens the page in the Windows settings.
"""
import ntpath
import os
import re
import subprocess
import sys

from ..dialer import SCHEMES, DialError
from ..i18n import _

__all__ = ["OWN_ID", "HostError", "installed", "install_hint", "app_id", "list_phone_apps",
           "forward_to_app", "default_handler", "set_default", "request_autostart"]

OWN_ID = "CallSwitcher.URL"
APP_NAME = "Call Switcher"  # name under RegisteredApplications, written by the installer
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
USER_CHOICE = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\{scheme}\UserChoice"


class HostError(Exception):
    pass


def installed() -> bool:
    """Runs as the installed app, not from a checkout (default handler and autostart need that)."""
    return getattr(sys, "frozen", False)


def install_hint() -> str:
    return _("Install Call Switcher to make it the default for tel: links.")


def app_id(path: str) -> str:
    return path  # a ProgID such as "MicroSIP.URL"


def expand_command(template: str, url: str) -> str:
    """'"C:\\x\\phone.exe" "%1"' + URL -> the command line to run (like the shell does)."""
    template = re.sub(r'\s+"?%[*2-9]"?', "", template)  # arguments we have nothing for
    quoted = '"' + url.replace('"', "") + '"'
    command, count = re.subn(r'"%[1lL]"|%[1lL]', lambda m: quoted, template)
    return command if count else f"{template} {quoted}"


def _registry():
    import winreg
    return winreg


def _value(root, path: str, name: str = "") -> str:
    winreg = _registry()
    try:
        with winreg.OpenKey(root, path) as key:
            value = winreg.QueryValueEx(key, name)[0]
    except OSError:
        return ""
    return str(value) if value is not None else ""


def _values(root, path: str) -> list[tuple[str, str]]:
    winreg = _registry()
    try:
        key = winreg.OpenKey(root, path)
    except OSError:
        return []
    values = []
    with key:
        i = 0
        while True:
            try:
                name, value, _type = winreg.EnumValue(key, i)
            except OSError:
                return values
            values.append((name, str(value)))
            i += 1


def _command(prog_id: str) -> str:
    winreg = _registry()
    return _value(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command")


def _exe_name(command: str) -> str:
    exe = command[1:].split('"', 1)[0] if command.startswith('"') else command.split(" ", 1)[0]
    return ntpath.splitext(ntpath.basename(exe))[0]


def list_phone_apps() -> list[tuple[str, str]]:
    """(ProgID, name) of the installed apps that handle sip:/tel:/callto:, without Call Switcher."""
    winreg = _registry()
    apps = {}
    # Apps that register properly: RegisteredApplications -> Capabilities\URLAssociations.
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for name, capabilities in _values(root, r"Software\RegisteredApplications"):
            for scheme in SCHEMES:
                prog_id = _value(root, rf"{capabilities}\URLAssociations", scheme)
                if prog_id and prog_id != OWN_ID and _command(prog_id):
                    apps.setdefault(prog_id, name)
                    break
    # Older apps write the scheme itself as a class (HKCR\sip\shell\open\command).
    for scheme in SCHEMES:
        command = _command(scheme)
        if command and scheme not in apps:
            apps[scheme] = _exe_name(command) or scheme
    return sorted(apps.items(), key=lambda app: app[1].casefold())


def forward_to_app(url: str, prog_id: str, on_error):
    """Run the open command of the chosen app with the URL (no loop through the tel: default)."""
    if not prog_id:
        raise DialError(_("No phone app selected"))
    command = _command(prog_id)
    if not command:
        raise DialError(_("Phone app not found: {path}", path=prog_id))
    try:
        subprocess.Popen(expand_command(command, url), close_fds=True)
    except OSError as e:
        raise DialError(_("Could not start the phone app: {error}", error=e)) from e


def default_handler() -> str:
    """ProgID that opens tel: links, or '' if there is none."""
    winreg = _registry()
    return _value(winreg.HKEY_CURRENT_USER, USER_CHOICE.format(scheme="tel"), "ProgId")


def set_default():
    # Opens Settings > Apps > Default apps > Call Switcher, where the user picks the links.
    try:
        os.startfile(f"ms-settings:defaultapps?registeredAppUser={APP_NAME}")
    except OSError as e:
        raise HostError(str(e)) from e


def _api():
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                             ctypes.POINTER(wintypes.DWORD)]
    advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    return ctypes, wintypes, kernel32, advapi32


def _process_user(process) -> bytes | None:
    """The TOKEN_USER of a process (its first field points to the user's SID), or None."""
    ctypes, wintypes, kernel32, advapi32 = _api()
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(process, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
        return None
    try:
        size = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))  # TokenUser
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            return None
        return buffer
    finally:
        kernel32.CloseHandle(token)


def pipe_server_is_current_user(pipe: int) -> bool:
    """Does a process of the current user serve this named pipe (client handle)?

    Pipe names are visible to all users, so another user could create ours first.
    """
    ctypes, wintypes, kernel32, advapi32 = _api()
    pid = wintypes.ULONG()
    if not kernel32.GetNamedPipeServerProcessId(pipe, ctypes.byref(pid)):
        return False
    process = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not process:
        return False  # another user's process
    try:
        server = _process_user(process)
    finally:
        kernel32.CloseHandle(process)
    own = _process_user(kernel32.GetCurrentProcess())
    if server is None or own is None:
        return False
    sid = ctypes.POINTER(ctypes.c_void_p)
    return bool(advapi32.EqualSid(ctypes.cast(server, sid)[0], ctypes.cast(own, sid)[0]))


def request_autostart(enabled: bool, timeout: float = 0):
    winreg = _registry()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{sys.executable}" --background')
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
    except OSError as e:
        raise HostError(str(e)) from e
