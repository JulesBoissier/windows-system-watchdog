"""Behaviour of ``get_windows_info``: what the watchdog reports about the desktop.

The orchestrator uses this list to work out which window the user is looking at, so these
tests cover what goes in it (visible, real windows), what each entry carries, and how
z-order is reported.
"""

import pytest

from src.windows_utils import get_windows_info
from tests.conftest import FakeWindow

EDITOR = FakeWindow(3, "Code.exe", "main.py - Visual Studio Code", (0, 0, 1280, 1040))
BROWSER = FakeWindow(1, "chrome.exe", "Docs - Google Chrome", (640, 0, 1920, 1040))
TASKBAR = FakeWindow(2, "explorer.exe", "", (0, 1040, 1920, 1080))


def by_exe(info):
    return {w["exe_name"]: w for w in info}


def test_reports_each_visible_window(desktop):
    """Every visible top-level window is reported with exe name, title, rect and size.

    Why: these are the fields the orchestrator needs to attribute a point of regard
    (rect) and to label it on the dashboard (exe name and title).
    """
    desktop([BROWSER, EDITOR, TASKBAR])

    info = by_exe(get_windows_info())

    assert set(info) == {"Code.exe", "chrome.exe", "explorer.exe"}
    editor = info["Code.exe"]
    assert editor["title"] == "main.py - Visual Studio Code"
    assert tuple(editor["rect"]) == (0, 0, 1280, 1040)
    assert tuple(editor["size"]) == (1280, 1040)


def test_z_index_follows_stacking_order(desktop):
    """``z_index`` is 0 for the front-most window and increases toward the back.

    Why: the orchestrator resolves overlapping windows front to back. Z-order comes from
    walking the window stack, not from enumeration order (which the fake deliberately
    scrambles).
    """
    desktop([BROWSER, TASKBAR, EDITOR])

    info = by_exe(get_windows_info())

    assert info["chrome.exe"]["z_index"] < info["explorer.exe"]["z_index"]
    assert info["explorer.exe"]["z_index"] < info["Code.exe"]["z_index"]


@pytest.mark.parametrize(
    "hidden",
    [
        FakeWindow(4, "svchost.exe", "hidden", (0, 0, 800, 600), visible=False),
        FakeWindow(5, "tooltip.exe", "", (10, 10, 11, 11)),  # 1x1 helper window
    ],
)
def test_omits_invisible_and_degenerate_windows(desktop, hidden):
    """Hidden windows and windows of 1 pixel or less aren't reported.

    Why: Windows has hundreds of invisible or 1x1 helper windows. None of them can be looked
    at, and reporting them would only slow down the client's geometry work.
    """
    desktop([EDITOR, hidden])

    assert [w["exe_name"] for w in get_windows_info()] == ["Code.exe"]


def test_window_of_protected_process_is_still_reported(desktop):
    """A window whose process can't be inspected is still reported, without an exe name.

    Why: elevated apps (Task Manager, installers) and processes that exit mid-request are
    routine. One unreadable process mustn't make the whole request fail and stall the
    orchestrator's tick.
    """
    desktop([EDITOR, FakeWindow(6, None, "Task Manager", (0, 0, 800, 600))])

    titles = {w["title"] for w in get_windows_info()}

    assert titles == {"main.py - Visual Studio Code", "Task Manager"}


def test_window_closing_during_request_does_not_fail_it(desktop):
    """A window that closes between the two Win32 walks doesn't make the request fail.

    Why: windows are enumerated once for details and walked again for z-order. A window
    closing in between is rare but certain to happen eventually over a day of 2 s polls.
    """
    desktop([BROWSER, EDITOR], closes_during_enumeration=BROWSER.hwnd)

    assert "Code.exe" in by_exe(get_windows_info())
