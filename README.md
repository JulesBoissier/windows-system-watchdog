# Windows-OS-Watchdog
A Windows Service that streams location of displayed windows

Runs as a scheduled task in your desktop session (a real Windows service can't see your windows) and serves on port **8002** by default.

## Scripts

Run from an **administrator** PowerShell in this folder (`status_service.ps1` doesn't need admin):

| Script | What it does |
| --- | --- |
| `.\install_service.ps1 [-Port 8002]` | Creates the venv, installs dependencies, registers the logon task and starts it |
| `.\status_service.ps1` | Shows task state, `/health` result and the last lines of `watchdog.log` |
| `.\restart_service.ps1` | Restarts the task, e.g. after pulling code changes |
| `.\stop_service.ps1` | Stops the watchdog and removes the scheduled task |

Requires Python 3 on PATH (`py` or `python`). Re-run `install_service.ps1` after changing `requirements.txt` or the port. Shared names and paths live in `config.ps1`.
