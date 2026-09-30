"""watchlist.py — compute what the ⚡EP Candidates watchlist should contain right now, and the
diff against what it currently holds. The scheduled run applies the result through the TradingView
connector (mcp-watchlist-update-watchlist); this script never talks to TradingView itself.

Composition (TradingView section headers are plain "###NAME" entries):
  NASDAQ:QQQ                       regime reference, always first
  ###TODAY      today's ≥3★ names from Briefs/<today>.analyst.json (fallback: .grades.json)
  ###OPEN       Log notes with status: open
  ###WATCH      Log notes with status watch-event, or verdict watch and status evaluated
  ###AGING      ≥3★ names from the last 5 sessions that still hold their day-1 low (from outcomes.csv)

Prune rules (applied every run):
  - anything not in the sets above is removed (yesterday's TODAY names either age or drop)
  - AGING drops a name after 5 sessions, or as soon as outcomes.csv says the day-1 low broke
  - OPEN/WATCH names leave when Matt changes the note's status (closed / no-trade / skipped)

  python watchlist.py [--current "NASDAQ:QQQ,NASDAQ:ABC,..."]   → JSON {symbols, added, removed, lines}
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys

from common import BRIEFS, DATA, LOG, read_csv, today_et, prev_trading_day

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _fm(p):
    m = FM_RE.match(p.read_text())
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"^([A-Za-z_]\w*):\s*(.*?)\s*(#.*)?$", line)
            if mm:
                d[mm.group(1)] = mm.group(2).strip().strip('"')
    return d


def _sym(ticker: str, exchange: str | None) -> str:
    if ":" in ticker:
        return ticker
    return f"{exchange}:{ticker}" if exchange else ticker


def resolve_exchanges(tickers: list[str]) -> dict:
    """EXCHANGE for bare tickers via the TradingView scanner (one query)."""
    want = sorted({t for t in tickers if t and ":" not in t})
    if not want:
        return {}
    try:
        from tradingview_screener import Query, col
        _, df = (Query().select("name", "exchange").where(col("name").isin(want), col("exchange").isin(["NASDAQ", "NYSE", "AMEX"]))
                 .set_markets("america").limit(len(want) * 2).get_scanner_data())
        return {r["name"]: r["exchange"] for _, r in df.iterrows()}
    except Exception:
        return {}


STALE_WATCH_SESSIONS = 30


def desired(today: dt.date | None = None) -> dict:
    today = today or today_et()
    cands = read_csv(DATA / "candidates.csv")
    exch = {r["ticker"]: r.get("exchange") for r in cands if r.get("ticker")}
    # TODAY
    today_syms = []
    for name in (f"{today.isoformat()}.analyst.json", f"{today.isoformat()}.grades.json"):
        p = BRIEFS / name
        if p.exists():
            try:
                g = json.loads(p.read_text())
                today_syms = [_sym(t, exch.get(t)) for t, v in g.items() if int(v.get("grade", 0)) >= 3]
                break
            except Exception:
                continue
    # OPEN / WATCH from notes
    open_syms, watch_syms, stale = [], [], []
    notes = [(_fm(p), p) for p in sorted(LOG.glob("*.md"))]
    exch.update(resolve_exchanges([d.get("ticker", "") for d, _ in notes if d.get("type") == "ep-eval"]))
    for d, p in notes:
        if d.get("type") != "ep-eval":
            continue
        s = _sym(d.get("ticker", ""), exch.get(d.get("ticker", "")))
        try:
            age = (today - dt.date.fromisoformat(d.get("date", "1970-01-01"))).days
        except Exception:
            age = 0
        if d.get("status") == "open":
            open_syms.append(s)
        elif d.get("status") == "watch-event" or (d.get("verdict") == "watch" and d.get("status") == "evaluated"):
            if age > STALE_WATCH_SESSIONS * 7 // 5:
                stale.append(f"{d.get('ticker')} ({d.get('date')}, {d.get('status')})")   # pruned: resolve the note
            else:
                watch_syms.append(s)
    # AGING: ≥3★ in the last 5 sessions, day-1 low still holding
    outs = {(r["ticker"], r["date"]): r for r in read_csv(DATA / "outcomes.csv")}
    aging = []
    d = today
    for _ in range(5):
        d = prev_trading_day(d)
        for name in (f"{d.isoformat()}.analyst.json", f"{d.isoformat()}.grades.json"):
            p = BRIEFS / name
            if not p.exists():
                continue
            try:
                g = json.loads(p.read_text())
            except Exception:
                continue
            for t, v in g.items():
                if int(v.get("grade", 0)) < 3:
                    continue
                o = outs.get((t, d.isoformat()))
                if o and str(o.get("d1_low_held")) == "False":
                    continue  # broke day-1 low → prune
                aging.append(_sym(t, exch.get(t)))
            break
    def dedupe(xs, seen):
        out = []
        for x in xs:
            if x and x not in seen:
                seen.add(x); out.append(x)
        return out
    seen = {"NASDAQ:QQQ"}
    t_ = dedupe(today_syms, seen); o_ = dedupe(open_syms, seen); w_ = dedupe(watch_syms, seen); a_ = dedupe(aging, seen)
    symbols = ["NASDAQ:QQQ"]
    for hdr, xs in (("###TODAY", t_), ("###OPEN", o_), ("###WATCH", w_), ("###AGING", a_)):
        if xs:
            symbols += [hdr] + xs
    return {"symbols": symbols, "today": t_, "open": o_, "watch": w_, "aging": a_, "stale_watches": stale}


def main(argv):
    cur = []
    if "--current" in argv:
        cur = [s.strip() for s in argv[argv.index("--current") + 1].split(",") if s.strip()]
    want = desired()
    cur_set = {s for s in cur if not s.startswith("###")}
    want_set = {s for s in want["symbols"] if not s.startswith("###")}
    want["added"] = sorted(want_set - cur_set)
    want["removed"] = sorted(cur_set - want_set)
    want["lines"] = [f"Watchlist: {len(want_set) - 1} names — today {len(want['today'])}, open {len(want['open'])}, watch {len(want['watch'])}, aging {len(want['aging'])}",
                     f"Added: {', '.join(want['added']) or 'none'} · Removed: {', '.join(want['removed']) or 'none'}"]
    if want.get("stale_watches"):
        want["lines"].append("Stale watches pruned (resolve the note: closed / no-trade / skipped): " + "; ".join(want["stale_watches"]))
    print(json.dumps(want, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
