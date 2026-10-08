import threading
import time

import pytest
import uvicorn

from blattwerk import db
from blattwerk.app import STATIC, app


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def server():
    """The app on a real port, for Chromium to call as it does in production."""
    assert (STATIC / "index.html").is_file(), "build the frontend first: mise run build"
    server = uvicorn.Server(uvicorn.Config(app, port=0, log_level="warning"))
    thread = threading.Thread(target=server.run)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    server.should_exit = True
    thread.join()
