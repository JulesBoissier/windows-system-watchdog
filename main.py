import argparse
import sys

import uvicorn
from fastapi import FastAPI
from screeninfo import get_monitors as screeninfo_get_monitors

from src.clicks import ClickRecorder
from src.dpi import enable_dpi_awareness
from src.windows_utils import get_windows_info

# Before any window or monitor query: rects and monitors in physical pixels.
DPI_AWARE = enable_dpi_awareness()

app = FastAPI()
clicks = ClickRecorder()  # recording starts on the first /clicks request


@app.get("/")
def root():
    return {
        "message": "System Watchdog is Running",
        "version": "",
        "uptime": "",
        "routes": ["/", "/health", "/windows_info", "/get_monitors", "/clicks"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/windows_info")
def windows_info():
    return get_windows_info()


@app.get("/get_monitors")
def get_monitors():
    return screeninfo_get_monitors()


@app.get("/clicks")
def get_clicks(after: int = 0):
    """Left clicks with sequence number > ``after``: ``{recording, last_seq, clicks}``.

    The first request starts recording (opt-in). Each click is ``{seq, x, y, t}`` with
    absolute desktop coordinates (physical pixels) and ``t`` = Windows ``time.time()``,
    the same clock as the webcam service's ``/frame_at``.
    """
    recording = clicks.ensure_started()
    return {"recording": recording, "last_seq": clicks.log.last_seq, "clicks": clicks.log.since(after)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int, default=8002, help="Port to run the server on"
    )
    parser.add_argument(
        "--log-file", help="Append stdout and stderr to this file instead of the console"
    )
    args = parser.parse_args()

    # Under pythonw.exe (used by the scheduled task) there is no console and
    # sys.stdout/sys.stderr are None, which crashes uvicorn's logging setup.
    if args.log_file:
        log = open(args.log_file, "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = log

    uvicorn.run(app, host="0.0.0.0", port=args.port)
