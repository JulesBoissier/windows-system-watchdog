"""The watchdog's HTTP contract with the orchestrator.

``activity-orchestration-client/src/backend/clients/system_watchdog_client.py`` reads these
routes. A change that breaks a test here needs a matching change there.
"""

import importlib
from types import SimpleNamespace

import pytest
import screeninfo
from fastapi.testclient import TestClient

from tests.conftest import FakeWindow

MONITORS = [
    screeninfo.Monitor(x=0, y=0, width=2560, height=1440, name="PRIMARY", is_primary=True),
    screeninfo.Monitor(x=-1920, y=0, width=1920, height=1080, name="LEFT", is_primary=False),
]


@pytest.fixture
def api(monkeypatch):
    # main.py imports get_monitors by name at import time, so patch the source and reload.
    monkeypatch.setattr(screeninfo, "get_monitors", lambda: MONITORS)
    import main

    main = importlib.reload(main)
    return TestClient(main.app)


def test_health(api):
    """``GET /health`` answers 200 with ``{"status": "ok"}``.

    Why: the orchestrator checks this before every tick.
    """
    r = api.get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_windows_info_returns_json_list(api, desktop):
    """``GET /windows_info`` returns a JSON list with ``exe_name``, ``title``, ``rect`` and ``z_index``.

    Why: this is the payload shape the orchestrator's client parses. ``rect`` must be
    ``[left, top, right, bottom]`` in absolute desktop pixels.
    """
    desktop([FakeWindow(1, "Code.exe", "main.py", (-1920, 0, 0, 1080))])

    body = api.get("/windows_info").json()

    assert isinstance(body, list)
    (entry,) = body
    assert entry["exe_name"] == "Code.exe"
    assert entry["title"] == "main.py"
    assert entry["rect"] == [-1920, 0, 0, 1080]
    assert entry["z_index"] == 0


def test_get_monitors_lists_displays(api):
    """``GET /get_monitors`` lists each display's position and size in desktop pixels.

    Why: monitor geometry is needed to map calibration coordinates to the desktop. Serving
    it from the watchdog gives the orchestrator the same view of the monitors Windows
    uses for window rects, even when the orchestrator runs elsewhere (WSL, Docker).
    """
    body = api.get("/get_monitors").json()

    assert [(m["x"], m["y"], m["width"], m["height"]) for m in body] == [
        (0, 0, 2560, 1440),
        (-1920, 0, 1920, 1080),
    ]
