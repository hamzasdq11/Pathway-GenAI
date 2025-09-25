# equinova_terminal/utils/market_data.py
from __future__ import annotations
import threading
import time
from typing import List, Dict
import yfinance as yf

class YFinancePoller:
    """
    Polls Yahoo Finance every N seconds for given tickers.
    Returns a dict per symbol with last/percent change etc.
    """
    def __init__(self, symbols: List[str], interval_sec: int = 5):
        self.symbols = symbols
        self.interval_sec = max(2, interval_sec)
        self._stop = threading.Event()
        self._latest: Dict[str, Dict] = {}
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def get_snapshot(self) -> Dict[str, Dict]:
        # shallow copy to avoid races
        return dict(self._latest)

    def _run(self):
        while not self._stop.is_set():
            try:
                data = yf.download(
                    tickers=" ".join(self.symbols),
                    period="1d",
                    interval="1m",
                    threads=True,
                    progress=False
                )
                now = {}
                for sym in self.symbols:
                    try:
                        last_close = float(data["Close"][sym].dropna().iloc[-1])
                        prev_close = float(data["Close"][sym].dropna().iloc[-2])
                        change = last_close - prev_close
                        pct = (change / prev_close) * 100 if prev_close else 0.0
                        now[sym] = {
                            "last": round(last_close, 4),
                            "change": round(change, 4),
                            "pct": round(pct, 4),
                        }
                    except Exception:
                        try:
                            last_close = float(data["Close"].dropna().iloc[-1])
                            prev_close = float(data["Close"].dropna().iloc[-2])
                            change = last_close - prev_close
                            pct = (change / prev_close) * 100 if prev_close else 0.0
                            now[sym] = {
                                "last": round(last_close, 4),
                                "change": round(change, 4),
                                "pct": round(pct, 4),
                            }
                        except Exception:
                            pass
                self._latest = now
            except Exception:
                pass
            self._stop.wait(self.interval_sec)