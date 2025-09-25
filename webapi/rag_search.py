import json, os, numpy as np
from typing import List, Dict

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
INDEX_FILE = os.path.join(CACHE_DIR, "rag_index.json")


def _embed(q: str) -> np.ndarray:
    """Single query embedding"""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.embeddings.create(model="text-embedding-3-small", input=q)
    return np.array(res.data[0].embedding, dtype=np.float32)


def rag_search(query: str, topk: int = 3) -> List[Dict[str, str]]:
    """Search cached RAG index for relevant news titles"""
    if not os.path.exists(INDEX_FILE):
        return []

    with open(INDEX_FILE, "r") as f:
        idx = json.load(f)

    qvec = _embed(query)
    scored = []
    for it in idx.get("items", []):
        v = np.array(it.get("vector", []), dtype=np.float32)
        if v.size:
            sim = float(np.dot(qvec, v) / (np.linalg.norm(qvec) * np.linalg.norm(v)))
            scored.append({"title": it["title"], "published": it["published"], "score": sim})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:topk]