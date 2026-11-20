"""Per-monitor DPI awareness for the watchdog process."""

import sys


def enable_dpi_awareness() -> bool:
    """Make Windows report physical pixels to this process. Returns whether it is DPI-aware.

    Without it, on monitors scaled above 100%, Windows hands this process virtualised
    (scaled-down) window rects and monitor sizes, which don't match the physical pixels
    the gaze calibration and the benchmark capture tool use. Must run before the first
    window or monitor query; later calls can't change the process's awareness.
    """
    if sys.platform != "win32":
        return False
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):  # Windows < 8.1
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            return False
    return bool(ctypes.windll.user32.IsProcessDPIAware())
