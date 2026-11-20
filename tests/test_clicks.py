"""Click recording for implicit calibration: the log and the ``/clicks`` route."""

import importlib

import pytest
import screeninfo
from fastapi.testclient import TestClient

from src.clicks import ClickLog, ClickRecorder


def test_log_returns_clicks_after_a_sequence_number():
    """``since(after)`` returns only newer clicks, oldest first.

    Why: the orchestrator polls every tick with the last sequence number it processed, so
    each click is used exactly once.
    """
    log = ClickLog()
    for i in range(3):
        log.add(10 * i, 20 * i, 100.0 + i)

    assert [c["seq"] for c in log.since(1)] == [2, 3]
    assert log.since(3) == []
    assert log.last_seq == 3


def test_log_is_bounded():
    """Only the most recent clicks are kept.

    Why: clicks are kept in memory for as long as the watchdog runs; an unbounded list
    would grow all day. Sequence numbers keep increasing, so a client notices a gap.
    """
    log = ClickLog(maxlen=5)
    for i in range(12):
        log.add(i, i, float(i))

    assert [c["seq"] for c in log.since(0)] == [8, 9, 10, 11, 12]


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(screeninfo, "get_monitors", lambda: [])
    import main

    main = importlib.reload(main)
    started = []

    def fake_hook(click_log):
        started.append(click_log)
        return True

    monkeypatch.setattr(main, "clicks", ClickRecorder(start_hook=fake_hook))
    return TestClient(main.app), main.clicks, started


def test_recording_starts_only_when_clicks_are_requested(api):
    """No hook is installed until a client asks for clicks; then it starts once.

    Why: recording clicks is opt-in. The watchdog runs all the time, but only an
    orchestrator with implicit calibration enabled asks for clicks.
    """
    client, recorder, started = api

    assert started == []
    client.get("/clicks")
    client.get("/clicks")

    assert len(started) == 1


def test_clicks_route_returns_new_clicks(api):
    """``/clicks?after=N`` returns ``{recording, last_seq, clicks}`` with clicks newer than N.

    Why: this is the contract the orchestrator polls each tick. Coordinates are absolute
    desktop pixels, the same space as window rects and monitors.
    """
    client, recorder, _ = api
    first = client.get("/clicks").json()
    recorder.log.add(-1500, 300, 1700000000.5)
    recorder.log.add(200, 400, 1700000001.0)

    body = client.get("/clicks", params={"after": first["last_seq"] + 1}).json()

    assert body["recording"] is True
    assert body["last_seq"] == 2
    assert body["clicks"] == [{"seq": 2, "x": 200, "y": 400, "t": 1700000001.0}]


def test_recording_unavailable_is_reported(monkeypatch):
    """Where the hook can't be installed (not Windows, or refused), ``recording`` is false.

    Why: the orchestrator then turns implicit calibration off with a warning instead of
    waiting forever for clicks.
    """
    recorder = ClickRecorder(start_hook=lambda log: False)

    assert recorder.ensure_started() is False
