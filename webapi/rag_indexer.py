import os, json, time, threading, math, hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any
import numpy as np
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
# Use the same cache file produced by pathway_livebus.py
CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache", "live_snapshot.json"))
INDEX_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache", "rag_index.json"))

# --- Embeddings (OpenAI) ---
try:
    from openai import OpenAI
    _emb = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _emb = None

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _embed_batch(texts: List[str]) -> List[List[float]]:
    if not _emb:
        raise RuntimeError("OpenAI client not available")
    # small, fast embedding model
    model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
    out = _emb.embeddings.create(model=model, input=texts)  # type: ignore
    return [d.embedding for d in out.data]

def _load_json(path: str) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def _save_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)

def _normalize_news_items(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for it in snapshot.get("news", []) or []:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        # we can enrich later (source, url, summary…)
        items.append({
            "id": _hash(title),
            "title": title,
            "published": it.get("published") or "",
        })
    return items

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    da = np.linalg.norm(a); db = np.linalg.norm(b)
    if da == 0 or db == 0:
        return 0.0
    return float(np.dot(a, b) / (da * db))

def _build_or_update_index():
    snap = _load_json(CACHE_FILE)
    if not snap:
        return False, "no snapshot"
    # read existing index
    idx = _load_json(INDEX_FILE) or {"updated_at": None, "dim": None, "items": []}
    existing = {it["id"]: it for it in idx.get("items", [])}

    # new/changed items
    news = _normalize_news_items(snap)
    new_titles = [it for it in news if it["id"] not in existing]

    if not new_titles:
        return True, f"no new items (total {len(existing)})"

    # embed new titles
    vecs = _embed_batch([x["title"] for x in new_titles])
    dim = len(vecs[0]) if vecs else idx.get("dim")
    for it, v in zip(new_titles, vecs):
        it["vector"] = v
        existing[it["id"]] = it

    # persist
    idx = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "dim": dim,
        "items": list(existing.values()),
    }
    _save_json(INDEX_FILE, idx)
    return True, f"indexed {len(new_titles)} new (total {len(existing)})"

def _writer_loop(interval_sec: int = 30):
    while True:
        try:
            ok, msg = _build_or_update_index()
            if ok:
                print(f"[ragbus] {msg}")
            else:
                print(f"[ragbus] WARN: {msg}")
        except Exception as e:
            print("[ragbus] ERROR:", e)
        time.sleep(interval_sec)

if __name__ == "__main__":
    # run in foreground for now
    _writer_loop(30)
