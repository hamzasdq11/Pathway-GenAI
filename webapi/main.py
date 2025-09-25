from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
import os
import json, time
from dotenv import load_dotenv
import json
import pathlib
import time
from datetime import datetime, timezone
from webapi.rag_search import rag_search
# cache file written by pathway_livebus.py
CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache", "live_snapshot.json"))

def read_cached_snapshot():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None
    
from webapi.live_context import (
    get_market_snapshot,
    get_news_snapshot,
    build_live_context,
)

app = FastAPI(title="Pathway-GenAI Bridge", version="0.1.0")

# Allow Tauri frontend to connect
origins = [
    "http://localhost:1420",  # Tauri dev
    "http://127.0.0.1:1420",  # Tauri dev alternative
    "http://localhost:1421",  # Tauri dev (changed port)
    "http://127.0.0.1:1421",  # Tauri dev alternative
    "tauri://localhost",      # Tauri app itself
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # safe for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "live_snapshot.json")

def _load_cached_snapshot():
    try:
        with open(CACHE_FILE) as f:
            j = json.load(f)
        return j
    except Exception:
        return None

def _format_cached_context(j):
    if not j:
        return None
    # prefer the prebuilt context string; fall back to a compact line
    ctx = j.get("context")
    if ctx:
        return ctx
    mk = j.get("markets", [])
    heads = "; ".join([h.get("title", "") for h in (j.get("news", [])[:5])])
    row = " | ".join([f"{m['symbol']}: {m['last']} ({m['d1_pct']}%)" for m in mk[:5]])
    ts = j.get("ts_utc", "?")
    return f"(Live snapshot @ {ts})\nMarkets: {row}\nTop headlines: {heads}"

# ------------------- Health & Test Endpoints -------------------

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

# ------------------- Cached snapshot (from Pathway livebus) -------------------

CACHE_PATH = pathlib.Path(__file__).with_name("cache") / "live_snapshot.json"

def read_cached_snapshot() -> Optional[Dict[str, Any]]:
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None

# ------------------- OpenAI Chat Endpoint -------------------

# Load .env so OPENAI_API_KEY is available when running via uvicorn
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(env_path))

from openai import OpenAI

_openai_client = None
try:
    _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("✅ OpenAI client initialized")
except Exception as e:
    print("❌ DEBUG: OpenAI init failed:", e)
    _openai_client = None

class ChatIn(BaseModel):
    message: str
    model: str = "gpt-4o-mini"
    include_live: bool = True
    symbols: Optional[List[str]] = None
    include_rag: bool = True         # NEW
    rag_k: int = 3                   # NEW

class ChatOut(BaseModel):
    reply: str

class LiveOut(BaseModel):
    ts_utc: Optional[str] = None
    age_sec: Optional[float] = None
    stale: bool = True
    markets: List[Dict[str, Any]]
    news: List[Dict[str, Any]]
    context: str

@app.post("/chat", response_model=ChatOut)
def chat(req: ChatIn):
    """
    Minimal chat endpoint for EquiNova AI tab.
    """
    if not _openai_client or not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OpenAI not configured on server")

    try:
        sys_content = "You are EquiNova AI assistant. Be concise and helpful."
        if req.include_live:
           snap = _load_cached_snapshot()
           cached_ctx = _format_cached_context(snap)
           if cached_ctx:
              sys_content += "\n\n" + cached_ctx
           else:
               try:
                  sys_content += "\n\n" + build_live_context(req.symbols)
               except Exception:
                  sys_content += "\n\n(Live snapshot unavailable)"
        if req.include_rag:
            try:
                hits = rag_search(req.message, topk=max(1, min(10, req.rag_k)))
                if hits:
                    rag_lines = "\n".join(f"- {h['title']} ({h.get('published','')})" for h in hits)
                    sys_content += "\n\nRAG context (top headlines related to the user prompt):\n" + rag_lines
            except Exception as _e:
                # keep chat working even if RAG lookup fails
                pass

        result = _openai_client.chat.completions.create(
            model=req.model,
            messages=[
                {"role": "system", "content": sys_content},
                {"role": "user", "content": req.message},
            ],
            temperature=0.2,
        )
        reply = result.choices[0].message.content
        return ChatOut(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
CACHE_FILE = pathlib.Path(__file__).parent / "cache" / "live_snapshot.json"

def _read_cached_live(max_stale_sec: int = 120) -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        # Fallback: build on-demand (slower, but keeps the UI alive)
        mkts = get_market_snapshot()
        nws  = get_news_snapshot()
        ctx  = build_live_context()
        return {
            "ts_utc": None,
            "age_sec": None,
            "stale": True,
            "markets": mkts,
            "news": nws,
            "context": ctx,
        }

    with open(CACHE_FILE, "r") as f:
        data = json.load(f)

    ts = data.get("ts_utc")
    age = None
    stale = True
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = max(0.0, time.time() - dt.timestamp())
            stale = age > max_stale_sec
        except Exception:
            pass

    return {
        "ts_utc": ts,
        "age_sec": age,
        "stale": stale,
        "markets": data.get("markets", []),
        "news": data.get("news", []),
        "context": data.get("context", ""),
    }
@app.get("/live", response_model=LiveOut)
def live():
    try:
        payload = _read_cached_live()
        return LiveOut(
            ts_utc=payload["ts_utc"],
            age_sec=payload["age_sec"],
            stale=payload["stale"],
            markets=payload["markets"],
            news=payload["news"],
            context=payload["context"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import Query

@app.get("/rag/search")
def rag_search_api(q: str = Query(..., description="User query"),
                   k: int = Query(3, description="Number of results")):
    """
    Search the RAG index for relevant news headlines.
    """
    try:
        hits = rag_search(q, topk=k)
        return hits
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))