# pathway_sources.py
import pathway as pw
import requests
import yfinance as yf
from datetime import datetime, timezone
from typing import List, Dict, Any

# --- Market data stream ---
def fetch_market(symbols: List[str]) -> List[Dict[str, Any]]:
    out = []
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d", interval="1d")
            if hist is None or hist.empty:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            d1 = (last - prev) / prev * 100.0 if prev else 0.0
            out.append({
                "symbol": sym,
                "last": round(last, 2),
                "d1_pct": round(d1, 2),
                "ts": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            continue
    return out

# --- News RSS stream ---
def fetch_news(feed_urls: List[str]) -> List[Dict[str, Any]]:
    items = []
    for url in feed_urls:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                continue
            import re
            titles = re.findall(r"<title>(.*?)</title>", resp.text, re.IGNORECASE)
            for t in titles[1:5]:
                items.append({
                    "title": t.strip(),
                    "ts": datetime.now(timezone.utc).isoformat()
                })
        except Exception:
            continue
    return items

# --- Pathway pipeline ---
def build_pipeline():
    symbols = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA",
    "GOOGL", "AMZN", "TSLA", "META", "NFLX",
    "JPM", "GS", "BAC", "WMT", "TCS.NS"
]
    feeds = [
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",         # WSJ Markets
    "https://www.investing.com/rss/news.rss",               # Investing.com
    "https://www.moneycontrol.com/rss/MCtopnews.xml",       # Moneycontrol India
    "https://www.cnbc.com/id/100003114/device/rss/rss.xml"  # CNBC Top News
]

    market_stream = pw.io.python.iterate(fetch_market(symbols))
    news_stream = pw.io.python.iterate(fetch_news(feeds))

    return market_stream, news_stream
