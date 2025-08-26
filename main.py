import argparse
import uvicorn
from fastapi import FastAPI

from src.windows_utils import get_windows_info

app = FastAPI()


@app.get("/")
def root():
    return {
        "message": "System Watchdog is Running",
        "version": "",
        "uptime": "",
        "routes": ["/", "/health", "/windows_info"],
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/windows_info")
def windows_info():
    return get_windows_info()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8002, help="Port to run the server on")
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port)