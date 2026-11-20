import argparse
import sys

import uvicorn
from fastapi import FastAPI
from screeninfo import get_monitors as screeninfo_get_monitors

from src.windows_utils import get_windows_info

app = FastAPI()


@app.get("/")
def root():
    return {
        "message": "System Watchdog is Running",
        "version": "",
        "uptime": "",
        "routes": ["/", "/health", "/windows_info", "/get_monitors"],
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
