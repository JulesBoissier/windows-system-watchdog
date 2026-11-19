# windows-system-watchdog

FastAPI app that reports the currently visible top-level windows on the Windows desktop (bounding rect, exe name, title, z-order). Part of the attention-tracking system — see `../CLAUDE.md`. Its only consumer is `activity-orchestration-client/src/backend/clients/system_watchdog_client.py`, which does all geometric processing (clipping, occlusion).

## Layout

- `main.py` — FastAPI app + argparse (`--port`, default 8002).
- `src/windows_utils.py` — pywin32/psutil logic: `EnumWindows` to collect visible windows, `GetTopWindow`/`GW_HWNDNEXT` walk to build a z-order map.
- `install_service.ps1` — creates `venv\`, installs requirements, registers the `WindowsSystemWatchdog` Scheduled Task, and starts a minimized instance immediately.

No pre-commit yet.

## Routes

- `GET /health` — `{"status": "ok"}`.
- `GET /windows_info` — list of `{hwnd, exe_name, title, rect:[l,t,r,b], size:[w,h], z_index}` for every visible window with area > 1px. `z_index` 0 = front-most. Rects are absolute virtual-desktop coordinates; minimized windows show up at about `-32000` and are filtered out by the client.
- `GET /get_monitors` — intended to return `screeninfo` monitors (broken on `main`, see below).

**Contract:** if you change the `/windows_info` shape, update `SystemWatchdogClient.compute_visible_windows` in the orchestrator in the same change.

## Tests

```bash
pip install -r requirements-dev.txt   # plus requirements.txt on Windows
pytest
```

`tests/conftest.py::FakeDesktop` replaces `win32gui`/`win32process`/`win32con`/`psutil` with a scripted desktop (and registers stub modules when pywin32 isn't installed), so the suite runs on Linux too. CI (`.github/workflows/python-ci.yml`) runs on `windows-latest`. Docstrings explain what each test covers and why the behaviour is designed that way. `xfail(strict=True)` marks bugs fixed on `fix/install-scripts`; remove each marker when merging that fix.

## Running

Windows only (pywin32). It can't run from WSL/Linux, but its tests can (see above).

```powershell
py main.py --port 8002
.\install_service.ps1 -Port 8002   # admin PowerShell
```

## Design notes

- **Scheduled Task, not a Windows service.** A service runs in Session 0 and can't see the interactive user's windows, so it's registered as a task that runs at logon as the current user (`RunLevel Highest`, interactive). This was a deliberate switch from an earlier NSSM service.
- **Thin server, smart client.** The watchdog returns raw window data; visibility/occlusion maths lives in the orchestrator (Shapely), so it can be unit-tested off Windows.
- Two separate enumerations (EnumWindows for data, GetTopWindow walk for z-order) are joined by `hwnd`.

## Gotchas (state of `main`)

- **`/get_monitors` recurses forever:** the route function is named `get_monitors` and shadows the imported `screeninfo.get_monitors`, so it calls itself → `RecursionError`. Fixed on `fix/install-scripts` (import aliased as `screeninfo_get_monitors`).
- **Scheduled task action is broken:** `install_service.ps1` passes `*> $LogFile 2>&1` as *arguments* to `python.exe` (no shell to interpret them), so argparse rejects them and the logon task fails. Only the immediate `Start-Process` launch works. `fix/install-scripts` rewrites this with `pythonw.exe` and a `--log-file` flag.
- `psutil.Process(pid).name()` can raise `NoSuchProcess`/`AccessDenied` (elevated or exiting processes) and a window can close between the two enumerations (`KeyError` in `add_z_index`). Both handled on `fix/install-scripts`.
- **`requirements.txt` is UTF-16 LE with BOM** on `main`.
- No `pid` is included in the response even though the client reads `w.get("pid")`.
- Coordinates depend on the process's DPI awareness; with display scaling ≠ 100% rects may not match the orchestrator's `screeninfo` monitor geometry.
