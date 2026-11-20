"""DPI awareness of the watchdog process."""

import sys

import pytest

from src.dpi import enable_dpi_awareness


@pytest.mark.skipif(sys.platform == "win32", reason="checks the non-Windows path")
def test_is_a_no_op_off_windows():
    """Off Windows, enabling DPI awareness does nothing and reports False.

    Why: the test suite (and imports of main.py) must work on Linux CI.
    """
    assert enable_dpi_awareness() is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_serving_process_is_dpi_aware():
    """Once ``main`` is imported (as uvicorn does), the process is DPI-aware.

    Why: with display scaling above 100%, a DPI-unaware process gets scaled-down window
    rects and monitor sizes. They then disagree with the physical pixels used by the
    calibration and benchmark tools, and gaze is attributed to the wrong windows.
    """
    import ctypes

    import main

    assert main.DPI_AWARE
    assert ctypes.windll.user32.IsProcessDPIAware()
