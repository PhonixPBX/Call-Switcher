"""The platform part of the Qt app (Linux or Windows): listing and starting phone apps, the
default handler for tel: links, and autostart. Both modules provide the same names:

    OWN_ID, HostError, installed(), install_hint(), app_id(path), list_phone_apps(),
    forward_to_app(url, path, on_error), default_handler(), set_default(), request_autostart(enabled)
"""
import sys

if sys.platform == "win32":
    from .host_windows import *  # noqa: F401,F403
else:
    from .host_linux import *  # noqa: F401,F403
