import ctypes
import sys
from typing import Any, Dict, List

import win32gui
import win32con
import win32process
import psutil


def build_z_index_map() -> Dict[str, int]:
    """Creates a list of Windows Handle and their associated Z-indices."""
    z_index_map = {}
    hwnd = win32gui.GetTopWindow(None)  # topmost window
    z = 0
    while hwnd:
        z_index_map[hwnd] = z
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        z += 1
    return z_index_map


DWMWA_CLOAKED = 14


def is_cloaked(hwnd) -> bool:
    """Whether the Desktop Window Manager hides this window although it is "visible".

    Windows keeps some windows visible but never draws them ("cloaked"): suspended UWP
    apps, windows on other virtual desktops, and shell overlays such as Click to Do and
    Windows Input Experience, which cover the whole screen in front of every app. Without
    this check every gaze point lands on them. Same test as the Alt+Tab list.
    """
    if sys.platform != "win32":
        return False
    cloaked = ctypes.c_int(0)
    result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        ctypes.c_void_p(hwnd), DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
    )
    return result == 0 and cloaked.value != 0


def win_enum_handler(hwnd, ctx):
    """Handler to be passed to EnumWindows to capture information for visible windows."""

    if win32gui.IsWindowVisible(hwnd) and not is_cloaked(hwnd):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            exe_name = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process exited mid-enumeration or is protected (e.g. elevated/system)
            exe_name = None
        # exe_path = process.exe()
        title = win32gui.GetWindowText(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        if width * height > 1:  # Ignores mini-windows or background processes
            ctx.append(
                {
                    "hwnd": hwnd,
                    "exe_name": exe_name,
                    # "exe_path": exe_path,
                    "title": title,
                    "rect": rect,
                    "size": (width, height),
                }
            )


def add_z_index(window_info, z_index_map):
    """Utility to append the Z-indices to the rest of the window information."""
    for window in window_info:
        # Windows closed between the two enumerations have no z-index; sort them last
        window["z_index"] = z_index_map.get(window["hwnd"], len(z_index_map))
    return window_info


def get_windows_info() -> List[Dict[str, Any]]:
    """Returns a list of information for each visible window currently visible."""
    window_info = []

    win32gui.EnumWindows(win_enum_handler, window_info)
    z_index_map = build_z_index_map()

    window_info = add_z_index(window_info, z_index_map)

    return window_info
