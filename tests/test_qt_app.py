import os
import sys

import pytest

if sys.platform == "darwin":
    pytest.skip("Linux and Windows app", allow_module_level=True)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from call_switcher.qt import app  # noqa: E402

PREFIX = "org.phonixpbx.callswitcher-"


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_pipe_name_is_random_and_kept(tmp_path):
    name = app.pipe_name(tmp_path / "Call Switcher")
    assert name.startswith(PREFIX) and len(name) == len(PREFIX) + 32
    assert app.pipe_name(tmp_path / "Call Switcher") == name
    assert app.pipe_name(tmp_path / "other") != name


def test_pipe_name_renew(tmp_path):
    name = app.pipe_name(tmp_path)
    renewed = app.pipe_name(tmp_path, renew=True)
    assert renewed != name
    assert app.pipe_name(tmp_path) == renewed


@pytest.mark.skipif(sys.platform != "win32", reason="Windows named pipes")
def test_pipe_server_of_current_user(qapp, tmp_path):
    from call_switcher.qt.host_windows import pipe_server_is_current_user

    name = app.pipe_name(tmp_path)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    assert server.listen(name), server.errorString()
    try:
        sock = QLocalSocket()
        sock.connectToServer(name)
        assert sock.waitForConnected(2000), sock.errorString()
        assert int(sock.socketDescriptor()) not in (0, -1)
        assert pipe_server_is_current_user(int(sock.socketDescriptor()))
        sock.abort()
    finally:
        server.close()
