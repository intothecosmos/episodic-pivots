"""market.py — daily market table `data/market.csv` (EP data capture v2.1, step 2).

One row per trading day: index trend fields for QQQ/SPY/IWM/XBI, VIX close, rubric Gate 0 (the SAME rule
as scan.regime(), via scan.gate0_rule), EOD breadth from one TradingView scanner query, scan/EOD event
counts, and the trailing-10-scan-day health of live EP outcomes. Backfilled to 2025-04-01 so the
historical baseline can be regime-split; appended nightly.

Reads   data_sources.history() daily bars (stockanalysis 5Y → nasdaq → yfinance), yfinance ^VIX
        (fallback: CBOE VIX_History.csv), data/candidates.csv (scan_hits, ep10_*), data/outcomes.csv (ep10_*),
        data/eod_events.csv (eod_events; blank until step 3 exists), the TradingView scanner (live breadth).
Writes  data/market.csv — keyed by `date`; --today replaces that date's row and refreshes the index/VIX/
        gate0/count columns of the previous 2 rows (keeping their breadth), so a stale same-day close
        from a cached source self-heals the next night.

Columns (fixed order; new columns append at the END only)
  date
  {qqq,spy,iwm,xbi}_{close,sma10,sma20,sma50,sma10_slope3_pct,sma20_slope3_pct,above10,above20,s10_gt_s20,
                      sessions_since_cross,dist_sma10_pct,dist_sma20_pct,dist_52w_high_pct}
  vix_close
  gate0 (green|red; QQQ SMA10 > SMA20 and both rising vs 3 sessions ago), gate0_sessions
  up4_count, down4_count, up4_ratio_10d, pct_above_sma20, pct_above_sma50, new_52w_highs, new_52w_lows,
  breadth_universe, breadth_basis
  scan_hits, eod_events
  ep10_gap_held_pct, ep10_d1low_held_pct, ep10_median_ret5d
  computed_at

Definitions
  slope3_pct            SMA today ÷ SMA three sessions ago − 1, in %.
  sessions_since_cross  consecutive sessions (incl. today) with the current s10_gt_s20 state; 1 = flip day.
  gate0_sessions        same counting for gate0 (1 = the session it flipped).
  dist_52w_high_pct     close ÷ max daily high of the trailing 252 sessions (incl. today) − 1, in %.
  breadth               live days only (the scanner is a snapshot, not history): universe = scan.py's base
                        universe (US common stock, cap ≥ $100M); up4/down4 = day change ≥ +4% / ≤ −4%;
                        new highs/lows = today's high ≥ 52w high / low ≤ 52w low. breadth_basis =
                        `eod_scanner`; blank on backfilled rows. up4_ratio_10d = Σup4 ÷ (Σup4+Σdown4) over
                        the trailing 10 rows that have breadth — blank until 10 live rows exist.
  scan_hits             unique tickers in candidates.csv dated that day (any snapshot).
  ep10_*                outcomes.csv rows whose trigger_date is one of the trailing 10 scan days (distinct
                        candidates.csv dates ≤ that day): gap_held = d1_close > prev_close (rows with a
                        D1 close); d1low_held = d1_low_held over rows with ≥ 2 sessions known;
                        median ret_5d over rows with ret_5d. Outcomes are allowed to be backfilled, so on
                        a re-run these refresh for recent rows; they are health gauges, not grades.
  vix_close             yfinance ^VIX daily close; days it lacks are filled from CBOE's VIX_History.csv
                        (official, published next morning). Both are the same CBOE series.

Source quirk (2026-10-30): stockanalysis's 5Y history endpoint can serve the current day from a cached
intraday snapshot (close/volume lower than the 1Y endpoint minutes later), and history() caches it for 6h.
Both modes therefore fetch the uncached 1Y range as well and, per date, keep the row with the larger
volume (the later snapshot of a session can only have more volume).

Usage
  python market.py --backfill [--start 2025-04-01]   # rebuild every row up to the last complete session
  python market.py --today [--date YYYY-MM-DD]       # append/replace one row (+ refresh the 2 before it)
  python market.py --verify                           # gate0/SMA vs candidates.csv and the Briefs
Functions return None instead of raising; a source that fails leaves its columns blank.
"""
from __future__ import annotations

import datetime as dt
import statistics as st
import sys

from common import CHROME_UA, DATA, get, is_trading_day, now_et, prev_trading_day, read_csv, today_et, write_csv
from data_sources import _from_stockanalysis, history

MARKET = DATA / "market.csv"
INDEX_SYMS = ["QQQ", "SPY", "IWM", "XBI"]
INDEX_FIELDS = ["close", "sma10", "sma20", "sma50", "sma10_slope3_pct", "sma20_slope3_pct", "above10", "above20",
                "s10_gt_s20", "sessions_since_cross", "dist_sma10_pct", "dist_sma20_pct", "dist_52w_high_pct"]
BREADTH_COLUMNS = ["up4_count", "down4_count", "up4_ratio_10d", "pct_above_sma20", "pct_above_sma50",
                   "new_52w_highs", "new_52w_lows", "breadth_universe", "breadth_basis"]
MARKET_COLUMNS = (["date"]
                  + [f"{s.lower()}_{f}" for s in INDEX_SYMS for f in INDEX_FIELDS]
                  + ["vix_close", "gate0", "gate0_sessions"]
                  + BREADTH_COLUMNS
                  + ["scan_hits", "eod_events", "ep10_gap_held_pct", "ep10_d1low_held_pct", "ep10_median_ret5d",
                     "computed_at"])
BACKFILL_START = "2025-04-01"
LOOKBACK_52W = 252
EP10_DAYS = 10


# ---------- sources ----------

def _merge_fresher(a: list[dict] | None, b: list[dict] | None) -> list[dict] | None:
    """Union of two daily-bar lists keyed by date; on a clash keep the row with the larger volume
    (a later snapshot of the same session can only have more volume)."""
    out: dict[str, dict] = {}
    for rows in (a or [], b or []):
        for r in rows:
            cur = out.get(r["d"])
            if cur is None or (r.get("v") or 0) > (cur.get("v") or 0):
                out[r["d"]] = r
    return sorted(out.values(), key=lambda r: r["d"]) or None


def daily_bars(sym: str, fresh: bool = True) -> list[dict] | None:
    """Daily bars oldest→newest, ≥ 2 years. fresh=True (default) also pulls the uncached 1Y range so a
    stale same-day row in the cached 5Y history is replaced (see the source quirk in the module docstring)."""
    h = history(sym, years=2)
    rows = h["rows"] if h else None
    if fresh:
        rows = _merge_fresher(rows, _from_stockanalysis(sym, "1Y"))
    return rows


def vix_closes() -> dict[str, float]:
    """{date: close} from yfinance ^VIX, filled from CBOE where yfinance has no row. {} if both fail."""
    out: dict[str, float] = {}
    try:
        import yfinance as yf
        df = yf.download("^VIX", period="3y", interval="1d", progress=False, auto_adjust=False)
        if df is not None and len(df):
            if hasattr(df.columns, "levels"):
                df.columns = [c[0] for c in df.columns]
            for d, r in df.iterrows():
                c = r.get("Close")
                if c == c and c is not None:
                    out[d.strftime("%Y-%m-%d")] = round(float(c), 2)
    except Exception:
        pass
    txt = get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv", ua=CHROME_UA)
    if txt:
        for line in txt.splitlines()[1:]:
            try:
                m, d, y = line.split(",")[0].split("/")
                iso = f"{y}-{m}-{d}"
                if iso not in out:
                    out[iso] = round(float(line.split(",")[4]), 2)
            except Exception:
                continue
    return out


def breadth_snapshot() -> dict | None:
    """One scanner query over scan.py's base universe → breadth counts for today. None on failure."""
    try:
        from tradingview_screener import Query
        from scan import _base_conds
        q = (Query().select("name", "change", "close", "SMA20", "SMA50", "price_52_week_high", "price_52_week_low",
                            "high", "low").where(*_base_conds()).set_markets("america").limit(8000))
        n, df = q.get_scanner_data()
        if df is None or len(df) == 0:
            return None
        ch, close = df["change"], df["close"]
        pa20 = (close > df["SMA20"]) & df["SMA20"].notna()
        pa50 = (close > df["SMA50"]) & df["SMA50"].notna()
        return {"up4_count": int((ch >= 4).sum()), "down4_count": int((ch <= -4).sum()),
                "pct_above_sma20": round(100.0 * pa20.sum() / df["SMA20"].notna().sum(), 1),
                "pct_above_sma50": round(100.0 * pa50.sum() / df["SMA50"].notna().sum(), 1),
                "new_52w_highs": int((df["high"] >= df["price_52_week_high"]).sum()),
                "new_52w_lows": int((df["low"] <= df["price_52_week_low"]).sum()),
                "breadth_universe": int(len(df)), "breadth_basis": "eod_scanner"}
    except Exception:
        return None


# ---------- pure computations ----------

def _sma(c: list[float], n: int, i: int):
    return sum(c[i - n + 1:i + 1]) / n if i + 1 >= n else None


def _pct(a, b, nd=2):
    return round((a / b - 1.0) * 100.0, nd) if a is not None and b else None


def index_series(bars: list[dict]) -> dict[str, dict]:
    """{date: {field: value}} for every session in `bars` (fields blank until enough history)."""
    c = [b["c"] for b in bars]
    hi = [b["h"] for b in bars]
    out: dict[str, dict] = {}
    state = None
    run = 0
    for i, b in enumerate(bars):
        s10, s20, s50 = _sma(c, 10, i), _sma(c, 20, i), _sma(c, 50, i)
        s10p, s20p = _sma(c, 10, i - 3) if i >= 3 else None, _sma(c, 20, i - 3) if i >= 3 else None
        gt = (s10 > s20) if (s10 is not None and s20 is not None) else None
        if gt is not None:
            run = run + 1 if gt == state else 1
            state = gt
        h52 = max(hi[max(0, i - LOOKBACK_52W + 1):i + 1]) if i + 1 >= LOOKBACK_52W else None
        out[b["d"]] = {
            "close": round(c[i], 2),
            "sma10": round(s10, 2) if s10 else None, "sma20": round(s20, 2) if s20 else None,
            "sma50": round(s50, 2) if s50 else None,
            "sma10_slope3_pct": _pct(s10, s10p, 3) if s10 and s10p else None,
            "sma20_slope3_pct": _pct(s20, s20p, 3) if s20 and s20p else None,
            "above10": (c[i] > s10) if s10 else None, "above20": (c[i] > s20) if s20 else None,
            "s10_gt_s20": gt, "sessions_since_cross": run if gt is not None else None,
            "dist_sma10_pct": _pct(c[i], s10), "dist_sma20_pct": _pct(c[i], s20),
            "dist_52w_high_pct": _pct(c[i], h52),
        }
    return out


def gate0_series(qqq_bars: list[dict]) -> dict[str, dict]:
    """{date: {gate0, gate0_sessions}} using scan.gate0_rule on the closes up to and including each date."""
    from scan import gate0_rule
    c = [b["c"] for b in qqq_bars]
    out: dict[str, dict] = {}
    state, run = None, 0
    for i, b in enumerate(qqq_bars):
        g = gate0_rule(c[:i + 1])
        if not g:
            continue
        run = run + 1 if g["state"] == state else 1
        state = g["state"]
        out[b["d"]] = {"gate0": state, "gate0_sessions": run}
    return out


def scan_hit_counts(cands: list[dict]) -> dict[str, int]:
    by: dict[str, set] = {}
    for r in cands:
        by.setdefault(r.get("date", ""), set()).add(r.get("ticker", ""))
    return {d: len(s) for d, s in by.items() if d}


def eod_event_counts() -> dict[str, int]:
    rows = read_csv(DATA / "eod_events.csv")
    out: dict[str, int] = {}
    for r in rows:
        out[r.get("date", "")] = out.get(r.get("date", ""), 0) + 1
    return out


def ep10_health(date: str, scan_days: list[str], outcomes: list[dict]) -> dict:
    """Health of live outcomes whose trigger_date falls in the trailing EP10_DAYS scan days ≤ date."""
    window = [d for d in scan_days if d <= date][-EP10_DAYS:]
    blank = {"ep10_gap_held_pct": None, "ep10_d1low_held_pct": None, "ep10_median_ret5d": None}
    if not window:
        return blank
    rows = [o for o in outcomes if o.get("trigger_date") in window]
    f = lambda v: float(v) if v not in (None, "") else None
    gap = [f(o["d1_close"]) > f(o["prev_close"]) for o in rows if f(o.get("d1_close")) and f(o.get("prev_close"))]
    held = [o["d1_low_held"] == "True" for o in rows
            if o.get("d1_low_held") in ("True", "False") and (f(o.get("sessions_known")) or 0) >= 2]
    r5 = [f(o["ret_5d"]) for o in rows if f(o.get("ret_5d")) is not None]
    return {"ep10_gap_held_pct": round(100.0 * sum(gap) / len(gap), 1) if gap else None,
            "ep10_d1low_held_pct": round(100.0 * sum(held) / len(held), 1) if held else None,
            "ep10_median_ret5d": round(st.median(r5), 2) if r5 else None}


def up4_ratio_10d(rows: list[dict]) -> None:
    """Fill up4_ratio_10d in place over the trailing 10 rows that carry breadth (rows sorted by date)."""
    hist: list[tuple[int, int]] = []
    for r in rows:
        if r.get("up4_count") in (None, "") or r.get("down4_count") in (None, ""):
            r["up4_ratio_10d"] = None
            continue
        hist.append((int(float(r["up4_count"])), int(float(r["down4_count"]))))
        if len(hist) < EP10_DAYS:
            r["up4_ratio_10d"] = None
            continue
        u = sum(x[0] for x in hist[-EP10_DAYS:])
        d = sum(x[1] for x in hist[-EP10_DAYS:])
        r["up4_ratio_10d"] = round(u / (u + d), 3) if (u + d) else None


# ---------- assembly ----------

def build_rows(dates: list[str], fresh: bool = True) -> list[dict] | None:
    """Index/VIX/gate0/count/ep10 columns for every date in `dates` (breadth left blank).
    None only if QQQ history is unavailable (gate0 is the point of the table)."""
    series, gate = {}, {}
    for s in INDEX_SYMS:
        bars = daily_bars(s, fresh=fresh)
        series[s] = index_series(bars) if bars else {}
        if s == "QQQ":
            if not bars:
                return None
            gate = gate0_series(bars)
    vix = vix_closes()
    cands = read_csv(DATA / "candidates.csv")
    hits = scan_hit_counts(cands)
    scan_days = sorted(hits)
    eod = eod_event_counts()
    outcomes = read_csv(DATA / "outcomes.csv")
    stamp = now_et().strftime("%Y-%m-%d %H:%M")
    rows = []
    for d in dates:
        row = {"date": d}
        for s in INDEX_SYMS:
            v = series[s].get(d, {})
            for f in INDEX_FIELDS:
                row[f"{s.lower()}_{f}"] = v.get(f)
        row["vix_close"] = vix.get(d)
        row.update(gate.get(d, {"gate0": None, "gate0_sessions": None}))
        row["scan_hits"] = hits.get(d)
        row["eod_events"] = eod.get(d) if eod else None
        row.update(ep10_health(d, scan_days, outcomes))
        row["computed_at"] = stamp
        rows.append(row)
    return rows


def sessions_between(start: str, end: str) -> list[str]:
    d, out = dt.date.fromisoformat(start), []
    stop = dt.date.fromisoformat(end)
    while d <= stop:
        if is_trading_day(d):
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def last_complete_session() -> str:
    """Today if it is a trading day and the session is over (≥ 16:05 ET), else the previous trading day."""
    now = now_et()
    t = now.date()
    if is_trading_day(t) and (now.hour, now.minute) >= (16, 5):
        return t.isoformat()
    return prev_trading_day(t).isoformat()


def save(rows_by_date: dict[str, dict]) -> int:
    rows = [rows_by_date[d] for d in sorted(rows_by_date)]
    up4_ratio_10d(rows)
    write_csv(MARKET, rows, MARKET_COLUMNS)
    return len(rows)


def backfill(start: str = BACKFILL_START) -> int | None:
    """Rebuild every row start → last complete session; breadth of existing live rows is preserved."""
    end = last_complete_session()
    dates = sessions_between(start, end)
    new = build_rows(dates)
    if new is None:
        return None
    existing = {r["date"]: r for r in read_csv(MARKET)}
    out: dict[str, dict] = {}
    for r in new:
        old = existing.get(r["date"])
        if old:
            for c in BREADTH_COLUMNS:
                r[c] = old.get(c) or None
        out[r["date"]] = r
    for d, r in existing.items():       # rows outside the rebuilt span (e.g. older starts) are kept
        out.setdefault(d, r)
    return save(out)


def today(date: str | None = None) -> dict | None:
    """Write the row for `date` (default: last complete session) with live breadth when `date` is today;
    refresh the non-breadth columns of the two previous rows. Returns the written row, None on failure."""
    date = date or last_complete_session()
    if not is_trading_day(dt.date.fromisoformat(date)):
        print(f"{date} is not a trading day — nothing to write")
        return {"date": date, "skipped": True}
    existing = {r["date"]: r for r in read_csv(MARKET)}
    prior = [d for d in sorted(existing) if d < date][-2:]
    new = build_rows(prior + [date], fresh=True)
    if new is None:
        return None
    for r in new:
        old = existing.get(r["date"])
        if old:
            for c in BREADTH_COLUMNS:
                r[c] = old.get(c) or None
        if r["date"] == date and date == today_et().isoformat():
            b = breadth_snapshot()
            if b:
                r.update(b)
        existing[r["date"]] = r
    if new[-1].get("qqq_close") is None:
        print(f"{date}: no QQQ bar yet — row written without index fields")
    save(existing)
    return new[-1]


# ---------- verification ----------

def verify() -> bool:
    """gate0 on market.csv vs regime_qqq on candidates.csv rows, and QQQ SMA10/20 vs the Briefs' Gate 0
    line. The morning rows judge the PREVIOUS completed session, so candidates dated D are compared with
    the market.csv row the brief names ("as of <date>"; default prev_trading_day(D)).
    Prints the comparison; True if all match."""
    import re
    from common import BRIEFS
    mk = {r["date"]: r for r in read_csv(MARKET)}
    cands = read_csv(DATA / "candidates.csv")
    by_day: dict[str, set] = {}
    for r in cands:
        if r.get("regime_qqq"):
            by_day.setdefault(r["date"], set()).add(r["regime_qqq"])
    ok = True
    print(f"{'scan day':10} {'judged':10} {'cands':6} {'market.csv':10} {'sma10 brief/mkt':18} {'sma20 brief/mkt':18} match")
    for d in sorted(by_day):
        judged = prev_trading_day(dt.date.fromisoformat(d)).isoformat()
        c = "/".join(sorted(by_day[d]))
        b10 = b20 = None
        p = BRIEFS / f"{d}.md"
        if p.exists():
            txt = p.read_text()
            mm = re.search(r"10d ([\d.]+) / 20d ([\d.]+)", txt)
            if mm:
                b10, b20 = float(mm.group(1)), float(mm.group(2))
            ma = re.search(r"as of (\d{4}-\d{2}-\d{2})", txt)
            if ma:
                judged = ma.group(1)      # the brief says which completed session it judged
        m = mk.get(judged, {})
        g_ok = m.get("gate0") == c
        s_ok = (b10 is None or abs(b10 - float(m.get("qqq_sma10") or 0)) <= 0.02) and \
               (b20 is None or abs(b20 - float(m.get("qqq_sma20") or 0)) <= 0.02)
        ok &= g_ok and s_ok
        print(f"{d:10} {judged:10} {c:6} {m.get('gate0') or '—':10} {str(b10):>7}/{m.get('qqq_sma10') or '—':<10} "
              f"{str(b20):>7}/{m.get('qqq_sma20') or '—':<10} {'OK' if g_ok and s_ok else 'MISMATCH'}")
    print("ALL MATCH" if ok else "MISMATCHES")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    arg = lambda k, default=None: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else default
    if "--backfill" in a:
        n = backfill(arg("--start", BACKFILL_START))
        print("backfill FAILED (no QQQ history)" if n is None else f"market.csv: {n} rows")
    elif "--today" in a:
        r = today(arg("--date"))
        if r is None:
            print("market.csv --today FAILED")
            sys.exit(1)
        if r.get("skipped"):
            sys.exit(0)
        print(f"market.csv {r['date']}: gate0 {r['gate0']} ({r['gate0_sessions']}) QQQ {r['qqq_close']} "
              f"sma10 {r['qqq_sma10']} sma20 {r['qqq_sma20']} VIX {r['vix_close']} "
              f"breadth up4 {r.get('up4_count')} down4 {r.get('down4_count')} ({r.get('breadth_basis') or 'none'}) "
              f"hits {r['scan_hits']}")
    elif "--verify" in a:
        sys.exit(0 if verify() else 1)
    else:
        print(__doc__)
