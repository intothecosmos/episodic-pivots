"""Keyless data sources with fallbacks. Each returns plain Python; None on failure.

history(ticker)      -> list of daily bars [{'d','o','h','l','c','v'}] oldest→newest (1Y+)
intraday_5m(ticker)  -> yfinance 5-min bars for the last ~60 days (pandas DataFrame) or None
earnings(ticker)     -> list of {'date','confirmed','period','time'} (past + future) or None
"""
from __future__ import annotations

import datetime as dt
import re

from common import CHROME_UA, cache_json, get


def _from_stockanalysis(ticker: str, rng: str = "1Y"):
    j = get(f"https://stockanalysis.com/api/symbol/s/{ticker.lower()}/history",
            params={"range": rng, "period": "Daily"}, json_out=True, ua=CHROME_UA)
    if not j or "data" not in j:
        return None
    rows = []
    for x in j["data"]:
        try:
            rows.append({"d": x["t"][:10], "o": float(x["o"]), "h": float(x["h"]),
                         "l": float(x["l"]), "c": float(x["c"]), "v": float(x["v"])})
        except Exception:
            continue
    rows.sort(key=lambda r: r["d"])
    return rows or None


def _from_nasdaq(ticker: str, years: int = 1):
    start = (dt.date.today() - dt.timedelta(days=365 * years + 10)).isoformat()
    j = get(f"https://api.nasdaq.com/api/quote/{ticker.upper()}/historical",
            params={"assetclass": "stocks", "fromdate": start, "limit": 9999},
            json_out=True, ua=CHROME_UA, headers={"Accept": "application/json"})
    try:
        rows_in = j["data"]["tradesTable"]["rows"]
    except Exception:
        return None
    num = lambda s: float(str(s).replace("$", "").replace(",", ""))
    rows = []
    for x in rows_in:
        try:
            m, d, y = x["date"].split("/")
            rows.append({"d": f"{y}-{m}-{d}", "o": num(x["open"]), "h": num(x["high"]),
                         "l": num(x["low"]), "c": num(x["close"]), "v": num(x["volume"])})
        except Exception:
            continue
    rows.sort(key=lambda r: r["d"])
    return rows or None


def _from_yfinance(ticker: str, period: str = "2y"):
    try:
        import yfinance as yf
        df = yf.download(ticker, period=period, progress=False, auto_adjust=False)
        if df is None or len(df) == 0:
            return None
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] for c in df.columns]
        rows = []
        for d, r in df.iterrows():
            rows.append({"d": d.strftime("%Y-%m-%d"), "o": float(r["Open"]), "h": float(r["High"]),
                         "l": float(r["Low"]), "c": float(r["Close"]), "v": float(r["Volume"])})
        return rows or None
    except Exception:
        return None


def history(ticker: str, years: int = 1) -> list[dict] | None:
    """Daily bars, oldest→newest. Source order: stockanalysis → nasdaq → yfinance."""
    # stockanalysis and nasdaq take class shares as BRK.B; only yfinance wants BRK-B
    t = ticker.upper()
    def produce():
        rows = _from_stockanalysis(t, "5Y" if years > 1 else "1Y")
        src = "stockanalysis"
        if not rows:
            rows, src = _from_nasdaq(t, years), "nasdaq"
        if not rows:
            rows, src = _from_yfinance(t.replace(".", "-"), f"{max(years,1)}y"), "yfinance"
        if not rows:
            return None
        return {"src": src, "rows": rows}
    return cache_json(f"hist_{t}_{years}", 6 * 3600, produce)


def intraday_5m(ticker: str):
    try:
        import yfinance as yf
        df = yf.download(ticker.upper().replace(".", "-"), period="60d", interval="5m",
                         progress=False, auto_adjust=False, prepost=False)
        if df is None or len(df) == 0:
            return None
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] for c in df.columns]
        return df
    except Exception:
        return None


def earnings(ticker: str) -> list[dict] | None:
    def produce():
        j = get(f"https://stockanalysis.com/api/symbol/s/{ticker.lower()}/earnings",
                json_out=True, ua=CHROME_UA)
        if not j or "data" not in j:
            return None
        out = []
        for x in j["data"]:
            try:
                out.append({"date": x.get("date", "")[:10], "confirmed": bool(x.get("confirmed")),
                            "period": x.get("period"), "time": x.get("time")})
            except Exception:
                continue
        return out or None
    return cache_json(f"earn_{ticker.upper()}", 24 * 3600, produce)


def next_earnings(ticker: str, after: dt.date) -> dict | None:
    rows = earnings(ticker) or []
    fut = [r for r in rows if r["date"] and r["date"] > after.isoformat()]
    fut.sort(key=lambda r: r["date"])
    return fut[0] if fut else None


def last_earnings(ticker: str, before_or_on: dt.date) -> dict | None:
    rows = earnings(ticker) or []
    past = [r for r in rows if r["date"] and r["date"] <= before_or_on.isoformat()]
    past.sort(key=lambda r: r["date"])
    return past[-1] if past else None


TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,6}$")
