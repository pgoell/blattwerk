"""A cheap password hash, one event loop, and a database that does not wait for the disk."""

import sqlite3
import threading
from concurrent.futures import Future
from types import SimpleNamespace

import anyio
import pytest
from anyio.from_thread import BlockingPortal
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from ui import serving

from blattwerk import auth, db


def one_loop():
    """One event loop for every TestClient of the run. Left alone, a client starts a loop for each
    request and ends it after, and on CI such a loop now and then never ends (#340). This one is
    never ended: its thread is a daemon and goes with the process."""
    made = Future()

    async def run():
        async with BlockingPortal() as portal:
            made.set_result(portal)
            await portal.sleep_until_stopped()

    threading.Thread(target=anyio.run, args=[run], daemon=True).start()
    return made.result()


def unsynced():
    """sqlite3 as the app's database module sees it, with connections that do not wait for the disk.

    SQLite asks the disk to confirm each commit. That guards the data against a power cut, which
    no test is about, and it took most of a test's start: signing a user up was 38 ms on an idle
    machine and 520 ms with sixteen workers at one disk, 4 ms without. Only the app's own
    connections: a test that opens the file itself gets what SQLite gives.
    """

    def connect(*args, **more):
        con = sqlite3.connect(*args, **more)
        con.execute("PRAGMA synchronous = OFF")
        return con

    return SimpleNamespace(**{**vars(sqlite3), "connect": connect})


@pytest.fixture(scope="session", autouse=True)
def cheap(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        # The real hash takes 64 MiB and a fifth of a second, and every test signs a user up.
        patch.setattr(auth, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
        # Between two tests too, no request may reach the data folder of the checkout.
        patch.setattr(db, "DATA_DIR", tmp_path_factory.mktemp("between"))
        patch.setattr(TestClient, "portal", one_loop())
        patch.setattr(db, "sqlite3", unsynced())
        yield


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def server():
    """The app on a real port, for Chromium to call as it does in production.

    One for the whole run: the app looks up the data folder with each request, so each test still
    has its own.
    """
    with serving() as url:
        yield url
