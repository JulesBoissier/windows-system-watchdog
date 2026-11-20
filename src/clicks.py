"""Recording mouse clicks, for implicit gaze calibration.

People look at what they click. Each click is a free calibration point: the orchestrator
pairs it with the webcam frame from that moment and sends it to the vision service.

Recording is opt-in: the hook only starts the first time a client asks for clicks
(``GET /clicks``), i.e. when the orchestrator runs with IMPLICIT_CALIBRATION enabled. Only
left-button presses are kept (position and time, nothing else), in memory, in a bounded
ring. Clicks injected by software are ignored.
"""

import logging
import sys
import threading
import time
from collections import deque
from typing import Callable, List, Optional

log = logging.getLogger(__name__)


class ClickLog:
    """Thread-safe ring of recent clicks with increasing sequence numbers."""

    def __init__(self, maxlen: int = 1000):
        self._clicks = deque(maxlen=maxlen)
        self._seq = 0
        self._lock = threading.Lock()

    def add(self, x: int, y: int, t: float):
        with self._lock:
            self._seq += 1
            self._clicks.append({"seq": self._seq, "x": int(x), "y": int(y), "t": float(t)})

    @property
    def last_seq(self) -> int:
        with self._lock:
            return self._seq

    def since(self, after: int) -> List[dict]:
        """Clicks with ``seq > after``, oldest first (older ones may have left the ring)."""
        with self._lock:
            return [c for c in self._clicks if c["seq"] > after]


class ClickRecorder:
    """Starts the mouse hook on first use and exposes the recorded clicks."""

    def __init__(self, start_hook: Optional[Callable[[ClickLog], bool]] = None):
        self.log = ClickLog()
        self._start_hook = start_hook or start_mouse_hook
        self._started = False
        self._recording = False
        self._lock = threading.Lock()

    def ensure_started(self) -> bool:
        """Start recording if not started yet. Returns whether clicks are being recorded."""
        with self._lock:
            if not self._started:
                self._started = True
                self._recording = bool(self._start_hook(self.log))
            return self._recording


def start_mouse_hook(click_log: ClickLog) -> bool:
    """Install a low-level mouse hook on a background thread. Returns False off Windows."""
    if sys.platform != "win32":
        return False
    ready = threading.Event()
    result = {"ok": False}
    thread = threading.Thread(
        target=_hook_thread, args=(click_log, ready, result), name="mouse-hook", daemon=True
    )
    thread.start()
    ready.wait(5)
    return result["ok"]


def _hook_thread(click_log: ClickLog, ready: threading.Event, result: dict):
    import ctypes
    from ctypes import wintypes as wt

    WH_MOUSE_LL = 14
    WM_LBUTTONDOWN = 0x0201
    LLMHF_INJECTED = 0x00000001
    LRESULT = ctypes.c_ssize_t

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", wt.POINT),  # per-monitor-aware screen coordinates (process is DPI-aware)
            ("mouseData", wt.DWORD),
            ("flags", wt.DWORD),
            ("time", wt.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
    user32.SetWindowsHookExW.restype = wt.HHOOK
    user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    kernel32.GetModuleHandleW.restype = wt.HMODULE

    @HOOKPROC
    def on_mouse(n_code, w_param, l_param):
        # Must return quickly: Windows drops slow low-level hooks.
        if n_code == 0 and w_param == WM_LBUTTONDOWN:
            info = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            if not info.flags & LLMHF_INJECTED:
                click_log.add(info.pt.x, info.pt.y, time.time())
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    hook = user32.SetWindowsHookExW(WH_MOUSE_LL, on_mouse, kernel32.GetModuleHandleW(None), 0)
    result["ok"] = bool(hook)
    if not hook:
        log.error("could not install the mouse hook (error %s)", ctypes.get_last_error())
    ready.set()
    if not hook:
        return
    msg = wt.MSG()  # low-level hooks are called from this thread's message loop
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
