"""Shared fixtures for the windows-system-watchdog test suite.

The watchdog's job is to read the Windows desktop through pywin32. Tests can't depend on
what happens to be open on the machine running them, so ``FakeDesktop`` replaces the three
Win32 modules and ``psutil.Process`` with a scripted desktop. The suite therefore runs on
Linux CI too: if pywin32 isn't installed, empty stand-in modules are registered so
``src.windows_utils`` can be imported, and every test patches in the fake.
"""

import importlib
import sys
import types
from dataclasses import dataclass
from typing import List, Optional, Tuple

import psutil
import pytest

for _name in ("win32gui", "win32con", "win32process"):
    try:
        importlib.import_module(_name)
    except ImportError:
        sys.modules[_name] = types.ModuleType(_name)

GW_HWNDNEXT = 2


@dataclass
class FakeWindow:
    hwnd: int
    exe: Optional[str]  # None: process is gone or protected
    title: str
    rect: Tuple[int, int, int, int]
    visible: bool = True

    @property
    def pid(self):
        return self.hwnd * 10


class FakeDesktop:
    """A scripted desktop. ``windows`` is in z-order, front-most first.

    ``EnumWindows`` deliberately reports windows in a different order (by hwnd), so tests
    can tell whether z-order comes from the stacking walk or from enumeration order.
    ``closes_during_enumeration`` simulates a window that disappears between the two Win32
    walks the watchdog makes.
    """

    def __init__(self, windows: List[FakeWindow], closes_during_enumeration=None):
        self.windows = windows
        self.closing = closes_during_enumeration
        self._by_hwnd = {w.hwnd: w for w in windows}

    # --- win32gui ---
    def EnumWindows(self, callback, ctx):
        for w in sorted(self.windows, key=lambda w: w.hwnd):
            callback(w.hwnd, ctx)

    def _stack(self):
        return [w.hwnd for w in self.windows if w.hwnd != self.closing]

    def GetTopWindow(self, _parent):
        stack = self._stack()
        return stack[0] if stack else 0

    def GetWindow(self, hwnd, cmd):
        assert cmd == GW_HWNDNEXT
        stack = self._stack()
        i = stack.index(hwnd)
        return stack[i + 1] if i + 1 < len(stack) else 0

    def IsWindowVisible(self, hwnd):
        return self._by_hwnd[hwnd].visible

    def GetWindowText(self, hwnd):
        return self._by_hwnd[hwnd].title

    def GetWindowRect(self, hwnd):
        return self._by_hwnd[hwnd].rect

    # --- win32process ---
    def GetWindowThreadProcessId(self, hwnd):
        return 1, self._by_hwnd[hwnd].pid

    # --- psutil ---
    def Process(self, pid):
        window = self._by_hwnd[pid // 10]
        if window.exe is None:
            raise psutil.AccessDenied(pid)
        return types.SimpleNamespace(name=lambda: window.exe, exe=lambda: window.exe)


@pytest.fixture
def desktop(monkeypatch):
    """Install a ``FakeDesktop`` into ``src.windows_utils``; returns a setter for its windows."""
    import src.windows_utils as wu

    def install(windows, **kwargs):
        fake = FakeDesktop(windows, **kwargs)
        monkeypatch.setattr(wu, "win32gui", fake)
        monkeypatch.setattr(wu, "win32process", fake)
        monkeypatch.setattr(wu, "win32con", types.SimpleNamespace(GW_HWNDNEXT=GW_HWNDNEXT))
        monkeypatch.setattr(
            wu,
            "psutil",
            types.SimpleNamespace(
                Process=fake.Process,
                NoSuchProcess=psutil.NoSuchProcess,
                AccessDenied=psutil.AccessDenied,
            ),
        )
        return fake

    return install
