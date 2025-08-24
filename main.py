import uvicorn
from fastapi import FastAPI

from src.windows_utils import get_windows_info

app = FastAPI()

@app.get("/")
def root():
    return {"message": "System Watchdog is Running"}

@app.get("/windows_info")
def windows_info():
    return get_windows_info()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)