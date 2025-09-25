from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

app = FastAPI(title="Pathway-GenAI Bridge", version="0.1.0")

# Allow Tauri frontend to connect
origins = [
    "http://localhost:1420",  # Tauri dev
    "http://127.0.0.1:1420",  # Tauri dev alternative
    "http://localhost:1421",  # Tauri dev (changed port)
    "http://127.0.0.1:1421",  # Tauri dev alternative
    "tauri://localhost"       # Tauri app itself
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 👈 allow everything for testing (safe for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.get("/markets/summary")
def markets_summary() -> List[Dict]:
    # stub market data — later we’ll wire this to live feeds
    return [
        {"symbol": "S&P 500", "last": 4984, "chg": -11.238, "d1": -2.25, "d7": -2.61},
        {"symbol": "Nasdaq 100", "last": 16095, "chg": -231.57, "d1": -1.44, "d7": 4.27},
        {"symbol": "Dow Jones", "last": 37970, "chg": -983.53, "d1": -2.47, "d7": -1.16},
    ]