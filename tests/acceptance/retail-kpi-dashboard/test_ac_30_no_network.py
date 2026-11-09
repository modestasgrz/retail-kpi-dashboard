"""AC-30 — Given every socket connect attempt raises, when the app runs each of the 5 pages in AppTest, then no page has an exception."""

import socket
from typing import Any

import pytest
from fixture import app

PAGES = [
    "views/overview.py",
    "views/trends.py",
    "views/flags.py",
    "views/table.py",
    "views/methodology.py",
]


def test_ac_30_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise OSError("network disabled in test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    at = app()
    assert not at.exception
    for path in PAGES:
        at.switch_page(path).run()
        assert not at.exception, path
