"""How the watchdog behaves when started the way the logon task starts it."""

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_log_file_captures_server_output_without_a_console(tmp_path):
    """With ``--log-file`` and no console streams, the watchdog starts and logs to the file.

    Why: the logon task runs ``pythonw.exe``, which has no console, so ``sys.stdout`` and
    ``sys.stderr`` are ``None``. Uvicorn crashes writing its startup log to them unless
    output goes to a file, and a task action can't redirect output itself. This runs
    ``main.py`` with both streams set to ``None``, exactly as under ``pythonw.exe``. Off
    Windows, empty stand-ins replace the pywin32 modules so the module can be imported.
    """
    log = tmp_path / "watchdog.log"
    script = (
        "import importlib, runpy, sys, types\n"
        "for name in ('win32gui', 'win32con', 'win32process'):\n"
        "    try:\n"
        "        importlib.import_module(name)\n"
        "    except ImportError:\n"
        "        sys.modules[name] = types.ModuleType(name)\n"
        "sys.stdout = sys.stderr = None\n"
        f"sys.argv = ['main.py', '--port', '0', '--log-file', {str(log)!r}]\n"
        "runpy.run_path('main.py', run_name='__main__')\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline and proc.poll() is None:
            if log.exists() and "Uvicorn running" in log.read_text(errors="replace"):
                break
            time.sleep(0.2)
        assert proc.poll() is None, f"server exited early:\n{log.read_text() if log.exists() else ''}"
        assert "Uvicorn running" in log.read_text(errors="replace")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
