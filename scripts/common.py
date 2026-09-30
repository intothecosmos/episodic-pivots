"""Shared helpers for the EP pipeline: paths, HTTP with the right headers per host,
ET time, trading calendar, CSV read/write with a stable schema.

All sources are keyless. Every helper degrades to None rather than raising, so a
missing field never kills a run; callers record the basis of whatever they got.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BRIEFS = ROOT / "Briefs"
LOG = ROOT / "Log"
REVIEWS = ROOT / "Reviews"
CACHE = ROOT / ".cache"
for _p in (DATA, BRIEFS, LOG, REVIEWS, CACHE):
    _p.mkdir(exist_ok=True)

ET = ZoneInfo("America/New_York")

CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
SEC_UA = "Matt Dufton EP research mattdufton@gmail.com"

# NYSE full-day holidays. Extend each December.
NYSE_HOLIDAYS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
    "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}


def now_et() -> dt.datetime:
    return dt.datetime.now(tz=ET)


def today_et() -> dt.date:
    return now_et().date()


def is_trading_day(d: dt.date | None = None) -> bool:
    d = d or today_et()
    return d.weekday() < 5 and d.isoformat() not in NYSE_HOLIDAYS


def prev_trading_day(d: dt.date | None = None) -> dt.date:
    d = (d or today_et()) - dt.timedelta(days=1)
    while not is_trading_day(d):
        d -= dt.timedelta(days=1)
    return d


def next_trading_day(d: dt.date) -> dt.date:
    d = d + dt.timedelta(days=1)
    while not is_trading_day(d):
        d += dt.timedelta(days=1)
    return d


_session = requests.Session()


def get(url: str, *, ua: str = CHROME_UA, headers: dict | None = None, params=None,
        timeout: int = 20, retries: int = 2, json_out: bool = False, sleep: float = 0.0):
    """GET with per-host headers. Returns text/json or None. Never raises."""
    h = {"User-Agent": ua, "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
         "Accept-Language": "en-US,en;q=0.9"}
    if headers:
        h.update(headers)
    for attempt in range(retries + 1):
        try:
            r = _session.get(url, headers=h, params=params, timeout=timeout)
            if r.status_code == 200:
                if sleep:
                    time.sleep(sleep)
                return r.json() if json_out else r.text
            if r.status_code in (403, 429, 503) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < retries:
                time.sleep(1.0)
                continue
            return None
    return None


def cache_json(key: str, ttl_s: int, producer):
    """Tiny file cache so re-runs in the same session don't re-hit sources."""
    p = CACHE / (key.replace("/", "_").replace(":", "_") + ".json")
    if p.exists() and time.time() - p.stat().st_mtime < ttl_s:
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    val = producer()
    if val is not None:
        p.write_text(json.dumps(val))
    return val


# ---------- CSV with stable schema ----------

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})


def upsert_csv(path: Path, new_rows: list[dict], columns: list[str], key: tuple[str, ...],
               overwrite: bool) -> int:
    """Insert rows keyed by `key`. If overwrite=False, existing rows are kept untouched
    (used for frozen candidate rows). If True, incoming fields overwrite existing ones
    (used for outcomes, which are recomputed as more days become known)."""
    existing = read_csv(path)
    norm = lambda v: "" if v is None else str(v)   # None must key as "" (what the CSV reads back)
    idx = {tuple(norm(r.get(k)) for k in key): r for r in existing}
    added = 0
    for r in new_rows:
        k = tuple(norm(r.get(c)) for c in key)
        if k in idx:
            if overwrite:
                idx[k].update({c: r[c] for c in r if c in columns})
        else:
            existing.append(r)
            idx[k] = r
            added += 1
    # keep union of columns so appended keys survive
    all_cols = list(columns)
    for r in existing:
        for c in r:
            if c not in all_cols:
                all_cols.append(c)
    write_csv(path, existing, all_cols)
    return added


def fmt(x, nd=1, pct=False, default="—"):
    try:
        if x is None or x == "":
            return default
        v = float(x)
        s = f"{v:,.{nd}f}"
        return s + "%" if pct else s
    except Exception:
        return default


def tv_symbol(exchange: str, ticker: str) -> str:
    return f"{exchange}:{ticker}"
