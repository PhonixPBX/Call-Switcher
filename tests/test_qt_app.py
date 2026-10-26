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
def test_pipe_peers_of_current_user(qapp, tmp_path):
    from call_switcher.qt.host_windows import pipe_name_is_free, pipe_peer_is_current_user

    name = app.pipe_name(tmp_path)
    assert pipe_name_is_free(name)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    assert server.listen(name), server.errorString()
    try:
        assert not pipe_name_is_free(name)
        client = QLocalSocket()
        client.connectToServer(name)
        assert client.waitForConnected(2000), client.errorString()
        assert int(client.socketDescriptor()) not in (0, -1)
        assert pipe_peer_is_current_user(int(client.socketDescriptor()), "server")
        assert server.waitForNewConnection(2000)
        accepted = server.nextPendingConnection()
        assert pipe_peer_is_current_user(int(accepted.socketDescriptor()), "client")
        client.abort()
    finally:
        server.close()


@pytest.mark.parametrize("found, renew", [("foreign", True), ("none", False)])
def test_foreign_pipe_starts_under_new_name(qapp, monkeypatch, found, renew):
    def send(message):
        if found == "foreign":
            raise app.ForeignServer()
        return False

    started = []

    class FakeApp:
        def __init__(self, qapp, renew=False):
            started.append(renew)

        def handle(self, message):
            pass

    monkeypatch.setattr(app, "send_to_running", send)
    monkeypatch.setattr(app, "App", FakeApp)
    monkeypatch.setattr(app, "QApplication", lambda argv: qapp)
    monkeypatch.setattr(qapp, "exec", lambda: 0)
    with pytest.raises(SystemExit):
        app.main(["--background"])
    assert started == [renew]
