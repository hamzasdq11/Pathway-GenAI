from __future__ import annotations
import os, time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import requests
import yfinance as yf

DEFAULT_SYMBOLS = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA",
    "GOOGL", "AMZN", "TSLA", "META", "NFLX",
    "JPM", "GS", "BAC", "WMT", "TCS.NS"
]
DEFAULT_FEEDS = [
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]

def _fetch_text(url: str, timeout: int = 5) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "EquiNova/1.0"})
        if r.status_code < 400 and r.text:
            return r.text
    except Exception:
        pass
    return None

def _parse_rss_titles(xml_text: str, limit: int = 10) -> List[Dict[str, str]]:
    import re
    items: List[Dict[str, str]] = []
    if not xml_text:
        return items
    titles = re.findall(r"<title>(.*?)</title>", xml_text, re.IGNORECASE | re.DOTALL)
    dates  = re.findall(r"<pubDate>(.*?)</pubDate>", xml_text, re.IGNORECASE | re.DOTALL)
    for i, t in enumerate(titles[1:limit+1], start=1):
        d = dates[i] if i < len(dates) else ""
        t = (t or "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        items.append({"title": t.strip(), "published": d.strip()})
    return items

def get_market_snapshot(symbols: Optional[List[str]] = None, max_symbols: int = 5) -> List[Dict[str, Any]]:
    syms = symbols or DEFAULT_SYMBOLS
    out: List[Dict[str, Any]] = []
    for sym in syms:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d", interval="1d")
            if hist is None or hist.empty or len(hist) < 2:
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2])
            d1 = (last - prev) / prev * 100.0 if prev else 0.0
            out.append({"symbol": sym, "last": round(last, 4), "d1_pct": round(d1, 2)})
            time.sleep(0.05)
        except Exception:
            continue
    return out

def get_news_snapshot(feeds: Optional[List[str]] = None, max_items: int = 50) -> List[Dict[str, str]]:
    feed_urls = (feeds or DEFAULT_FEEDS)[:3]
    items: List[Dict[str, str]] = []
    for url in feed_urls:
        xml = _fetch_text(url, timeout=5)
        titles = _parse_rss_titles(xml or "", limit=max_items // len(feed_urls) + 1)
        items.extend(titles)
    seen, deduped = set(), []
    for it in items:
        title = it.get("title","").strip()
        if title and title not in seen:
            deduped.append(it)
            seen.add(title)
        if len(deduped) >= max_items:
            break
    return deduped

def build_live_context(symbols: Optional[List[str]] = None) -> str:
    mkts = get_market_snapshot(symbols)
    news = get_news_snapshot(max_items=50)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"(Live snapshot @ {now})"]
    if mkts:
        row = " | ".join(f"{m['symbol']}: {m['last']} ({m['d1_pct']}%)" for m in mkts)
        parts.append("Markets: " + row)
    if news:
        heads = "; ".join(n['title'] for n in news[:5])
        parts.append("Top headlines: " + heads)
    return "\n".join(parts)
