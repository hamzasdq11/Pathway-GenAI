import os, time, json, threading
from datetime import datetime, timezone
import pathway as pw

# reuse your existing helpers
from webapi.live_context import get_market_snapshot, get_news_snapshot, build_live_context

CACHE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache", "live_snapshot.json"))

def _collect_once():
    """Pull markets + news once using the existing helpers."""
    mkts = get_market_snapshot()
    nws  = get_news_snapshot()
    ctx  = build_live_context()
    return {"ts_utc": datetime.now(timezone.utc).isoformat(), "markets": mkts, "news": nws, "context": ctx}

def _writer_loop(interval_sec: int = 20):
    """Simple file writer — we’ll swap this with Pathway sinks later if needed."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    while True:
        try:
            payload = _collect_once()
            with open(CACHE_FILE, "w") as f:
                json.dump(payload, f)
            print("[livebus] wrote snapshot @", payload["ts_utc"], flush=True)  # success log
        except Exception as e:
            print("[livebus] write error:", e, flush=True)
        time.sleep(interval_sec)

# --- Minimal Pathway graph (kept simple) ---
table = pw.debug.table_from_markdown("col\ninit\n")

@pw.udf
def annotate(_: str) -> str:
    return f"livebus-started@{datetime.now(timezone.utc).strftime('%H:%M:%S')}"

annotated = table.select(msg=annotate(table.col))
pw.debug.compute_and_print(annotated)

# Do one immediate write so the file exists right away
try:
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    _first = _collect_once()
    with open(CACHE_FILE, "w") as f:
        json.dump(_first, f)
    print("[livebus] initial snapshot @", _first["ts_utc"], flush=True)
except Exception as e:
    print("[livebus] initial write error:", e, flush=True)

# Start the background writer thread
_writer = threading.Thread(target=_writer_loop, args=(20,), daemon=False)
_writer.start()

# Keep Pathway engine alive
pw.run()
# Ensure process stays up even if Pathway graph completes
_writer.join()
