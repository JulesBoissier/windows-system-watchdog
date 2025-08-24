from typing import Dict, List, Any

import win32gui
import win32con

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


def win_enum_handler(hwnd, ctx):
    """Handler to be passed to EnumWindows to capture information for visible windows."""
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        # Append to the passed-in list instead of global
        ctx.append(
            {
                "hwnd": hwnd,
                "title": title,
                "rect": rect,
                "size": (width, height),
            }
        )


def add_z_index(window_info, z_index_map):
    """Utility to append the Z-indices to the rest of the window information."""
    for window in window_info:
        window["z_index"] = z_index_map[window["hwnd"]]
    return window_info


def get_windows_info() -> List[Dict[str, Any]]:
    """Returns a list of information for each visible window currently visible."""
    window_info = []

    win32gui.EnumWindows(win_enum_handler, window_info)
    z_index_map = build_z_index_map()

    window_info = add_z_index(window_info, z_index_map)

    return window_info
