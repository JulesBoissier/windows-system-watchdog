# windows-system-watchdog

FastAPI app that reports the currently visible top-level windows on the Windows desktop (bounding rect, exe name, title, z-order). Part of the attention-tracking system — see `../CLAUDE.md`. Its only consumer is `activity-orchestration-client/src/backend/clients/system_watchdog_client.py`, which does all geometric processing (clipping, occlusion).

## Layout

- `main.py` — FastAPI app + argparse (`--port`, default 8002; `--log-file`, needed under `pythonw.exe` where stdout/stderr are `None`).
- `src/windows_utils.py` — pywin32/psutil logic: `EnumWindows` to collect visible windows, `GetTopWindow`/`GW_HWNDNEXT` walk to build a z-order map.
- `src/dpi.py` — per-monitor DPI awareness for the process.
- `config.ps1` — shared names and paths, dot-sourced by the scripts below.
- `install_service.ps1` / `stop_service.ps1` / `restart_service.ps1` / `status_service.ps1` — manage the `WindowsSystemWatchdog` logon task, which runs `venv\Scripts\pythonw.exe main.py --log-file watchdog.log` as the current user.

No pre-commit yet.

## Routes

- `GET /health` — `{"status": "ok"}`.
- `GET /windows_info` — list of `{hwnd, exe_name, title, rect:[l,t,r,b], size:[w,h], z_index}` for every visible, non-cloaked window with area > 1px. `z_index` 0 = front-most. Rects are absolute virtual-desktop coordinates; minimized windows show up at about `-32000` and are filtered out by the client.
- `GET /get_monitors` — `screeninfo` monitors (`x`, `y`, `width`, `height`, `name`, `is_primary`, …) in the same desktop coordinates as window rects.

**Contract:** if you change the `/windows_info` shape, update `SystemWatchdogClient.compute_visible_windows` in the orchestrator in the same change.

## Tests

```bash
pip install -r requirements-dev.txt   # plus requirements.txt on Windows
pytest
```

`tests/conftest.py::FakeDesktop` replaces `win32gui`/`win32process`/`win32con`/`psutil` with a scripted desktop (and registers stub modules when pywin32 isn't installed), so the suite runs on Linux too. CI (`.github/workflows/python-ci.yml`) runs on `windows-latest`. Docstrings explain what each test covers and why the behaviour is designed that way.

## Running

Windows only (pywin32). It can't run from WSL/Linux, but its tests can (see above).

```powershell
py main.py --port 8002
.\install_service.ps1                # admin PowerShell: logon task on port 8002
.\status_service.ps1                 # task state, /health, tail of watchdog.log
```

## Design notes

- **Scheduled Task, not a Windows service.** A service runs in Session 0 and can't see the interactive user's windows, so it's registered as a task that runs at logon as the current user (`RunLevel Highest`, interactive). This was a deliberate switch from an earlier NSSM service.
- **Thin server, smart client.** The watchdog returns raw window data; visibility/occlusion maths lives in the orchestrator (Shapely), so it can be unit-tested off Windows.
- Two separate enumerations (EnumWindows for data, GetTopWindow walk for z-order) are joined by `hwnd`.

## Gotchas

- **Cloaked windows are skipped** (`is_cloaked`, DWM `DWMWA_CLOAKED`): Windows reports them visible but never draws them. Windows 11's Click to Do overlay is a full-screen, front-most cloaked window that captured every gaze point before this filter; Windows Input Experience and apps on other virtual desktops are cloaked too.
- `psutil` can't inspect elevated or exiting processes: their windows are still reported, with `exe_name: null`. A window closing between the two enumerations is sorted last instead of failing the request.
- No `pid` is included in the response even though the client reads `w.get("pid")`.
- **DPI-aware:** `main.py` calls `src.dpi.enable_dpi_awareness()` at import, before any window or monitor query, so rects and `/get_monitors` are physical pixels (same as the benchmark capture tool). Anything that queries windows must happen after it; awareness can't be changed later in the process.
