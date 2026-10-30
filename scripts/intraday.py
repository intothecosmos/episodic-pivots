"""intraday.py — raw intraday bar archive (EP data capture v2.1, step 1).

Persist what expires. yfinance keeps 1-min bars ~30 days, 5-min ~60 days, 1-hour ~730 days.
This module stores them in the repo so the past stays analyzable; features are derived later
(outcomes.py, step 4) and never depend on a live fetch.

Layout
  data/intraday/{TICKER}/{D0}.csv.gz        event window: sessions D0..D0+5 (pre/post included)
  data/intraday/{TICKER}/{D0}.pre14.csv.gz  lookback: the 14 sessions before D0 (own-window RVOL baseline)
  data/intraday/coverage.csv                one row per expected file: status, basis, sessions, complete

File columns: ts (ET, ISO with offset), open, high, low, close, volume, basis (1m|5m|1h).
D0 = first trading day ≥ the event date (same convention as outcomes.trigger_date).
Basis by age of D0 at fetch time: ≤29d → 1m (fallback 5m → 1h); ≤59d → 5m (→ 1h); else 1h.
The lookback is 5m when its first session is ≤59d old, else 1h. Every row carries its basis.
Only completed sessions are stored (a session counts as complete after 20:05 ET), so a file
fetched before D0+5 has passed is `complete=False` and --update refetches it later.

Known source quirks (verified 2026-10-30, CVNA/CMG/NRXP/CPRI/AMZN/META):
  - Extended-hours bars carry prices but ZERO volume. Premarket volume must come from the scanner
    snapshot (candidates.premarket_volume), never from these bars. pm_high/pm_low are fine.
  - One post-close bar (16:00–16:02) often carries a large late volume print.
  - Regular-hours volume summed over bars does not reconcile with consolidated daily volume
    (observed 0.47×–1.72×). Derive volume ratios within this feed (own-window RVOL) or scale by
    the daily bar (step 4 records `vol_scale`). OHLC reconciles exactly.
  - Lookback files are capped at 5m (the RVOL baseline needs the first 5-min bar only).

Usage
  python intraday.py --backfill [--source live|hist|eod|all] [--budget-min N]  # events with no file yet
  python intraday.py --update                      # refetch incomplete event files whose D5 has passed
  python intraday.py --event TICKER DATE [--source live]
  python intraday.py --verify TICKER DATE          # archive regular-session OHLCV vs daily bars
  python intraday.py --report                      # coverage summary (for the weekly review)
Idempotent: existing complete files are never refetched. Symbol mismatches are logged, not silent.
"""
from __future__ import annotations

import datetime as dt
import gzip
import logging
import sys
import time
from pathlib import Path

from common import DATA, ET, is_trading_day, next_trading_day, now_et, prev_trading_day, read_csv, today_et, write_csv

INTRADAY = DATA / "intraday"
COVERAGE = INTRADAY / "coverage.csv"
INTRADAY.mkdir(exist_ok=True)

COVERAGE_COLUMNS = [
    "ticker", "date", "window", "source", "basis", "status", "rows", "sessions", "sessions_target",
    "first_ts", "last_ts", "complete", "attempts", "fetched_at", "note",
]
FILE_COLUMNS = ["ts", "open", "high", "low", "close", "volume", "basis"]
EVENT_SESSIONS = 6          # D0..D5
LOOKBACK_SESSIONS = 14      # D-14..D-1
MAX_1M_AGE_DAYS = 29        # yfinance: 1m "must be within the last 30 days" (start time)
MAX_5M_AGE_DAYS = 59        # 5m: 60 days
MAX_1M_SPAN_DAYS = 7        # one 1m request covers at most 7 calendar days (8 works, 7 is safe)
SLEEP_S = 0.25
MAX_ATTEMPTS = 3            # empty/error files
MAX_STALE_ATTEMPTS = 2      # fetched-but-incomplete files whose D5 has passed (new listings: D0 has no bars)

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


# ---------- calendar ----------

def trigger_day(date: str) -> dt.date:
    d = dt.date.fromisoformat(date)
    while not is_trading_day(d):
        d += dt.timedelta(days=1)
    return d


def sessions_after(d0: dt.date, n: int) -> list[dt.date]:
    """d0 plus the next n-1 trading days (n sessions in total, d0 first)."""
    out = [d0]
    while len(out) < n:
        out.append(next_trading_day(out[-1]))
    return out


def sessions_before(d0: dt.date, n: int) -> list[dt.date]:
    out = []
    d = d0
    while len(out) < n:
        d = prev_trading_day(d)
        out.append(d)
    return sorted(out)


def last_complete_session(now: dt.datetime | None = None) -> dt.date:
    """Post-market ends 20:00 ET; a session is treated as complete from 20:05 ET."""
    now = now or now_et()
    d = now.date()
    if is_trading_day(d) and (now.hour, now.minute) >= (20, 5):
        return d
    return prev_trading_day(d)


def yahoo_symbol(ticker: str) -> str:
    return ticker.upper().replace(".", "-")


# ---------- fetch ----------

def _download(symbol: str, interval: str, start: dt.date, end_exclusive: dt.date):
    """Returns (DataFrame|None, note). Never raises. Backs off on rate limits."""
    import yfinance as yf
    note = ""
    for attempt in range(3):
        try:
            df = yf.download(symbol, start=start.isoformat(), end=end_exclusive.isoformat(), interval=interval,
                             prepost=True, progress=False, auto_adjust=False, threads=False)
        except Exception as e:  # network / parse
            note = f"{type(e).__name__}: {e}"[:160]
            if "429" in str(e) or "Too Many" in str(e):
                time.sleep(30 * (attempt + 1))
                continue
            time.sleep(1.0)
            continue
        err = ""
        try:
            import yfinance.shared as _shared                       # yfinance's per-symbol error text
            err = str(_shared._ERRORS.get(symbol, "") or "")
        except Exception:
            pass
        if df is None or len(df) == 0:
            if "Too Many" in err or "429" in err:
                time.sleep(30 * (attempt + 1))
                continue
            return None, (err[:160] if err else "empty")
        if hasattr(df.columns, "levels"):
            df.columns = [c[0] for c in df.columns]
        return df, err[:160]
    return None, note or "retries exhausted"


def _rows_from_df(df, basis: str, keep_sessions: set[dt.date]) -> list[dict]:
    idx = df.index.tz_convert(ET) if df.index.tz is not None else df.index.tz_localize("UTC").tz_convert(ET)
    rows = []
    seen = set()
    for ts, r in zip(idx, df.itertuples(index=False)):
        rec = r._asdict() if hasattr(r, "_asdict") else {}
        close = rec.get("Close")
        if close is None or close != close:   # NaN
            continue
        if ts.date() not in keep_sessions or ts in seen:
            continue
        seen.add(ts)
        vol = rec.get("Volume")
        rows.append({"ts": ts.isoformat(), "open": round(float(rec.get("Open")), 4), "high": round(float(rec.get("High")), 4),
                     "low": round(float(rec.get("Low")), 4), "close": round(float(close), 4),
                     "volume": int(vol) if vol == vol and vol is not None else 0, "basis": basis})
    rows.sort(key=lambda x: x["ts"])
    return rows


def _basis_for(start: dt.date, asof: dt.date, finest: str = "1m") -> list[str]:
    age = (asof - start).days
    order = ["1m", "5m", "1h"]
    if age > MAX_1M_AGE_DAYS:
        order = ["5m", "1h"]
    if age > MAX_5M_AGE_DAYS:
        order = ["1h"]
    return [b for b in order if order.index(b) >= order.index(finest)] if finest in order else order


def fetch_window(ticker: str, sessions: list[dt.date], asof: dt.date | None = None, finest: str = "1m") -> tuple[list[dict], str, str]:
    """Bars for the given sessions at the finest basis available (≤ `finest`). Returns (rows, basis, note)."""
    asof = asof or today_et()
    if not sessions:
        return [], "", "no completed sessions yet"
    start, last = sessions[0], sessions[-1]
    end_ex = last + dt.timedelta(days=1)
    keep = set(sessions)
    sym = yahoo_symbol(ticker)
    note = ""
    for basis in _basis_for(start, asof, finest):
        interval = {"1m": "1m", "5m": "5m", "1h": "1h"}[basis]
        rows: list[dict] = []
        if basis == "1m":
            s = start
            ok = True
            while s < end_ex:
                e = min(end_ex, s + dt.timedelta(days=MAX_1M_SPAN_DAYS))
                df, n = _download(sym, interval, s, e)
                time.sleep(SLEEP_S)
                if df is None:
                    note = n
                    # a chunk inside the window may legitimately be empty (holiday week); only fail
                    # when the chunk containing D0 is empty
                    if s == start:
                        ok = False
                        break
                else:
                    rows += _rows_from_df(df, basis, keep)
                s = e
            if ok and rows:
                return rows, basis, note
            continue
        df, n = _download(sym, interval, start, end_ex)
        time.sleep(SLEEP_S)
        if df is None:
            note = n
            continue
        rows = _rows_from_df(df, basis, keep)
        if rows:
            return rows, basis, note
        note = note or "no bars in window"
    return [], "", note or "empty"


# ---------- files ----------

def event_path(ticker: str, d0: dt.date) -> Path:
    return INTRADAY / ticker.upper() / f"{d0.isoformat()}.csv.gz"


def lookback_path(ticker: str, d0: dt.date) -> Path:
    return INTRADAY / ticker.upper() / f"{d0.isoformat()}.pre14.csv.gz"


def write_bars(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as f:
        f.write(",".join(FILE_COLUMNS) + "\n")
        for r in rows:
            f.write(",".join(str(r[c]) for c in FILE_COLUMNS) + "\n")


def read_bars(path: Path) -> list[dict]:
    if not path.exists():
        return []
    import csv
    with gzip.open(path, "rt", newline="") as f:
        out = []
        for r in csv.DictReader(f):
            for k in ("open", "high", "low", "close"):
                r[k] = float(r[k])
            r["volume"] = int(float(r["volume"]))
            out.append(r)
        return out


# ---------- coverage ----------

def load_coverage() -> dict[tuple, dict]:
    return {(r["ticker"], r["date"], r["window"]): r for r in read_csv(COVERAGE)}


def save_coverage(cov: dict[tuple, dict]) -> None:
    rows = sorted(cov.values(), key=lambda r: (r["date"], r["ticker"], r["window"]))
    write_csv(COVERAGE, rows, COVERAGE_COLUMNS)


def _cov_row(ticker, d0, window, source, basis, status, rows, sessions, target, complete, attempts, note):
    return {"ticker": ticker, "date": d0.isoformat(), "window": window, "source": source, "basis": basis,
            "status": status, "rows": len(rows), "sessions": sessions, "sessions_target": target,
            "first_ts": rows[0]["ts"] if rows else "", "last_ts": rows[-1]["ts"] if rows else "",
            "complete": complete, "attempts": attempts, "fetched_at": now_et().strftime("%Y-%m-%d %H:%M"), "note": note}


# ---------- events ----------

def events(source: str = "all") -> list[tuple[str, str, str]]:
    """(ticker, date, source) for every event the archive should hold. Deduped per ticker-day."""
    out: dict[tuple[str, str], str] = {}
    if source in ("hist", "all"):
        for r in read_csv(DATA / "historical_eps.csv"):
            if r.get("ticker") and r.get("date"):
                out.setdefault((r["ticker"].upper(), r["date"]), "hist")
    if source in ("live", "all"):
        for r in read_csv(DATA / "candidates.csv"):
            if r.get("ticker") and r.get("date"):
                out[(r["ticker"].upper(), r["date"])] = "live"     # live wins over hist on overlap
    if source in ("eod", "all"):
        for r in read_csv(DATA / "eod_events.csv"):              # step 4; absent until then
            if r.get("ticker") and r.get("date"):
                out.setdefault((r["ticker"].upper(), r["date"]), "eod")
    return sorted([(t, d, s) for (t, d), s in out.items()], key=lambda x: (x[1], x[0]))


def archive_event(ticker: str, date: str, source: str, cov: dict, *, force: bool = False, lookback: bool = True) -> list[str]:
    """Fetch (or refetch) one event's files. Returns one summary line per file touched."""
    d0 = trigger_day(date)
    lcs = last_complete_session()
    out = []
    # old events (>59d): both windows are 1h → one request for D-14..D5, split into the two files
    if lookback and _basis_for(d0, today_et()) == ["1h"]:
        ev_prev, lb_prev = cov.get((ticker, d0.isoformat(), "event")), cov.get((ticker, d0.isoformat(), "pre14"))
        ev_done = ev_prev and str(ev_prev.get("complete")) == "True" and event_path(ticker, d0).exists()
        lb_done = lb_prev and lb_prev.get("status") in ("fetched", "empty")
        if not (ev_done and lb_done) or force:
            ev_sessions = [s for s in sessions_after(d0, EVENT_SESSIONS) if s <= lcs]
            lb_sessions = sessions_before(d0, LOOKBACK_SESSIONS)
            rows, basis, note = fetch_window(ticker, lb_sessions + ev_sessions)
            ev_rows = [r for r in rows if r["ts"][:10] >= d0.isoformat()]
            lb_rows = [r for r in rows if r["ts"][:10] < d0.isoformat()]
            for window, wrows, wanted, path in (("event", ev_rows, sessions_after(d0, EVENT_SESSIONS), event_path(ticker, d0)),
                                                ("pre14", lb_rows, lb_sessions, lookback_path(ticker, d0))):
                got = sorted({r["ts"][:10] for r in wrows})
                complete = bool(wrows) and all(s.isoformat() in got for s in wanted)
                if wrows:
                    write_bars(path, wrows)
                status = "fetched" if wrows else ("error" if note and "retries" in note else "empty")
                n = note if status != "fetched" else ""
                if wrows and not complete and window == "pre14":
                    n = f"{len(got)} of {LOOKBACK_SESSIONS} sessions (recent listing?)"
                if wrows and not complete and window == "event" and got[0] > d0.isoformat():
                    n = f"first bar {got[0]} (new listing?)"
                prev = cov.get((ticker, d0.isoformat(), window))
                attempts = int(prev.get("attempts") or 0) + 1 if prev else 1
                cov[(ticker, d0.isoformat(), window)] = _cov_row(ticker, d0, window, source, basis, status, wrows, len(got),
                                                                   len(wanted), complete, attempts, n)
                out.append(f"{ticker} {d0} {window}: {status} {basis} {len(wrows)} rows {len(got)}/{len(wanted)} sessions"
                           f"{' complete' if complete else ''}{(' — ' + n) if n else ''}")
        return out
    # event window
    key = (ticker, d0.isoformat(), "event")
    prev = cov.get(key)
    if prev and str(prev.get("complete")) == "True" and not force and event_path(ticker, d0).exists():
        pass
    else:
        wanted = sessions_after(d0, EVENT_SESSIONS)
        avail = [s for s in wanted if s <= lcs]
        attempts = int(prev.get("attempts") or 0) + 1 if prev else 1
        if not avail:
            cov[key] = _cov_row(ticker, d0, "event", source, "", "pending", [], 0, EVENT_SESSIONS, False, attempts - 1,
                                "D0 session not complete yet")
            out.append(f"{ticker} {d0} event: pending (D0 not complete)")
        else:
            rows, basis, note = fetch_window(ticker, avail)
            got = sorted({r["ts"][:10] for r in rows})
            complete = bool(rows) and all(s.isoformat() in got for s in wanted)
            if rows:
                write_bars(event_path(ticker, d0), rows)
                status = "fetched"
                if got[0] > d0.isoformat():
                    note = f"first bar {got[0]} (new listing?)"
            else:
                status = "error" if note and note != "empty" and "not available" not in note and "no bars" not in note else "empty"
            cov[key] = _cov_row(ticker, d0, "event", source, basis, status, rows, len(got), EVENT_SESSIONS, complete, attempts, note)
            out.append(f"{ticker} {d0} event: {status} {basis} {len(rows)} rows {len(got)}/{EVENT_SESSIONS} sessions"
                       f"{' complete' if complete else ''}{(' — ' + note) if note and status != 'fetched' else ''}")
    # lookback window (the past; fetched once, refetched only with --force)
    if lookback:
        key = (ticker, d0.isoformat(), "pre14")
        prev = cov.get(key)
        if prev and prev.get("status") in ("fetched", "empty") and not force and (lookback_path(ticker, d0).exists() or prev.get("status") == "empty"):
            return out
        wanted = sessions_before(d0, LOOKBACK_SESSIONS)
        rows, basis, note = fetch_window(ticker, wanted, finest="5m")
        got = sorted({r["ts"][:10] for r in rows})
        complete = len(got) >= LOOKBACK_SESSIONS
        if rows:
            write_bars(lookback_path(ticker, d0), rows)
            status = "fetched"
        else:
            status = "empty"
        if rows and not complete:
            note = (note + "; " if note else "") + f"{len(got)} of {LOOKBACK_SESSIONS} sessions (recent listing?)"
        attempts = int(prev.get("attempts") or 0) + 1 if prev else 1
        cov[key] = _cov_row(ticker, d0, "pre14", source, basis, status, rows, len(got), LOOKBACK_SESSIONS, complete, attempts, note)
        out.append(f"{ticker} {d0} pre14: {status} {basis} {len(rows)} rows {len(got)}/{LOOKBACK_SESSIONS} sessions")
    return out


# ---------- commands ----------

def needs_refetch(r: dict | None, lcs: dt.date) -> bool:
    """Shared retry policy for an event-window coverage row.
    pending → yes once D0 is complete · incomplete with new sessions available → yes ·
    stale incomplete (D5 passed; typically a new listing with no bars on D0) → at most MAX_STALE_ATTEMPTS ·
    empty/error → at most MAX_ATTEMPTS."""
    if r is None:
        return True
    if str(r.get("complete")) == "True":
        return False
    attempts = int(r.get("attempts") or 0)
    d0 = dt.date.fromisoformat(r["date"])
    if d0 > lcs:
        return False                                    # D0 not complete yet; nothing to fetch
    if r.get("status") in ("empty", "error"):
        return attempts < MAX_ATTEMPTS
    wanted = sessions_after(d0, EVENT_SESSIONS)
    avail = len([s for s in wanted if s <= lcs])
    have = int(r.get("sessions") or 0)
    if wanted[-1] <= lcs:                               # stale: D5 has passed
        return attempts < MAX_STALE_ATTEMPTS
    return avail > have                                 # still filling in


def backfill(source: str, budget_min: float | None, limit: int | None) -> None:
    cov = load_coverage()
    lcs = last_complete_session()
    todo = []
    for t, d, s in events(source):
        d0 = trigger_day(d).isoformat()
        ev = cov.get((t, d0, "event"))
        lb = cov.get((t, d0, "pre14"))
        need_ev = needs_refetch(ev, lcs) or (ev is None)
        if ev is not None and ev.get("status") == "pending" and dt.date.fromisoformat(d0) > lcs:
            need_ev = False                             # still pending; --update picks it up later
        need_lb = not lb or (lb.get("status") == "error" and int(lb.get("attempts") or 0) < MAX_ATTEMPTS)
        if need_ev or need_lb:
            todo.append((t, d, s))
    print(f"backfill: {len(todo)} events to fetch (source={source}); coverage rows now {len(cov)}")
    t0 = time.time()
    done = 0
    for i, (t, d, s) in enumerate(todo):
        if limit and done >= limit:
            break
        if budget_min and (time.time() - t0) / 60 > budget_min:
            print(f"budget reached after {done} events; {len(todo) - done} remaining")
            break
        try:
            for line in archive_event(t, d, s, cov):
                print(line)
        except Exception as e:  # never lose the coverage log to one bad ticker
            print(f"{t} {d}: EXCEPTION {type(e).__name__}: {e}")
            cov[(t, trigger_day(d).isoformat(), "event")] = _cov_row(t, trigger_day(d), "event", s, "", "error", [], 0,
                                                                      EVENT_SESSIONS, False, 1, f"{type(e).__name__}: {e}"[:160])
        done += 1
        if done % 25 == 0:
            save_coverage(cov)
            print(f"-- {done}/{len(todo)} ({(time.time() - t0) / 60:.1f} min)")
    save_coverage(cov)
    print(f"backfill done: {done} events in {(time.time() - t0) / 60:.1f} min; {len(todo) - done} remaining")


def update() -> None:
    """Evening job: refetch event files that were incomplete when fetched and whose D5 has now passed
    (or whose D0 has completed since); up to 3 attempts per file once D5 is past."""
    cov = load_coverage()
    lcs = last_complete_session()
    n = 0
    for key, r in list(cov.items()):
        if r["window"] != "event" or not needs_refetch(r, lcs):
            continue
        for line in archive_event(r["ticker"], r["date"], r.get("source") or "live", cov, lookback=False):
            print(line)
        n += 1
        if n % 25 == 0:
            save_coverage(cov)
    # events that have no coverage row at all (new candidates today)
    known = {(k[0], k[1]) for k in cov}
    for t, d, s in events("all"):
        d0 = trigger_day(d).isoformat()
        if (t, d0) not in known:
            for line in archive_event(t, d, s, cov):
                print(line)
            n += 1
    save_coverage(cov)
    print(f"update: {n} events touched")


def verify(ticker: str, date: str) -> int:
    """Rebuild regular-session OHLCV from the archive and compare with the daily bar. Returns 0 if within tolerance."""
    from data_sources import history
    d0 = trigger_day(date)
    rows = [r for r in read_bars(event_path(ticker, d0)) if r["ts"][:10] == d0.isoformat()]
    if not rows:
        print(f"{ticker} {d0}: no archived bars")
        return 2
    basis = rows[0]["basis"]
    reg = [r for r in rows if "09:30:00" <= r["ts"][11:19] < "16:00:00"]
    if not reg:
        print(f"{ticker} {d0}: no regular-session bars")
        return 2
    o, h, l, c = reg[0]["open"], max(r["high"] for r in reg), min(r["low"] for r in reg), reg[-1]["close"]
    v = sum(r["volume"] for r in reg)
    hist = history(ticker, years=2)
    day = next((b for b in (hist or {}).get("rows", []) if b["d"] == d0.isoformat()), None)
    first = reg[0]
    or5 = [r for r in reg if r["ts"][11:16] < "09:35"]
    orh, orl = max(r["high"] for r in or5), min(r["low"] for r in or5)
    print(f"{ticker} {d0} archive ({basis}, {len(rows)} bars, {len(reg)} regular): O {o} H {h} L {l} C {c} V {v:,}  | first-5-min ORH {orh} ORL {orl}")
    if not day:
        print("daily bar: not available for comparison")
        return 1
    print(f"{ticker} {d0} daily   ({hist['src']}): O {day['o']} H {day['h']} L {day['l']} C {day['c']} V {int(day['v']):,}")
    tol = 0.01 if basis == "1m" else 0.02
    def close(a, b):
        return abs(a / b - 1) <= tol if b else False
    checks = {"open": close(o, day["o"]), "high": h <= day["h"] * (1 + tol) and h >= day["h"] * (1 - 0.03),
              "low": l >= day["l"] * (1 - tol) and l <= day["l"] * (1 + 0.03), "close": close(c, day["c"])}
    bad = [k for k, ok in checks.items() if not ok]
    ratio = (v / day["v"]) if day["v"] else None
    print(f"volume: regular-hours bars / consolidated daily = {ratio:.2f} (informational — Yahoo intraday volume does not reconcile; see module notes)"
          if ratio else "volume: daily volume unavailable")
    print("verify:", "OK" if not bad else f"MISMATCH on {bad} (tolerance {tol:.0%})")
    return 0 if not bad else 1


def report() -> str:
    cov = list(load_coverage().values())
    lines = []
    for window in ("event", "pre14"):
        rows = [r for r in cov if r["window"] == window]
        if not rows:
            continue
        by_src = {}
        for r in rows:
            by_src.setdefault(r.get("source") or "?", []).append(r)
        lines.append(f"{window}: {len(rows)} expected files")
        for src, rs in sorted(by_src.items()):
            fetched = [r for r in rs if r["status"] == "fetched"]
            comp = [r for r in rs if str(r.get("complete")) == "True"]
            bases = {}
            for r in fetched:
                bases[r["basis"]] = bases.get(r["basis"], 0) + 1
            empties = [r for r in rs if r["status"] == "empty"]
            errs = [r for r in rs if r["status"] == "error"]
            pend = [r for r in rs if r["status"] == "pending"]
            pct = 100 * len(fetched) / len(rs) if rs else 0
            lines.append(f"  {src}: fetched {len(fetched)}/{len(rs)} ({pct:.1f}%), complete {len(comp)}, "
                         f"bases {dict(sorted(bases.items()))}, empty {len(empties)}, error {len(errs)}, pending {len(pend)}")
            if empties:
                lines.append("    empty: " + ", ".join(f"{r['ticker']} {r['date']}" for r in empties[:15]) + (" …" if len(empties) > 15 else ""))
    size = sum(p.stat().st_size for p in INTRADAY.rglob("*.csv.gz"))
    lines.append(f"archive size: {size / 1e6:.1f} MB in {sum(1 for _ in INTRADAY.rglob('*.csv.gz'))} files")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    def opt(name, default=None):
        if name in argv:
            i = argv.index(name)
            return argv[i + 1] if i + 1 < len(argv) else default
        return default
    if "--backfill" in argv:
        b = opt("--budget-min")
        lim = opt("--limit")
        backfill(opt("--source", "all"), float(b) if b else None, int(lim) if lim else None)
        print(report())
        return 0
    if "--update" in argv:
        update()
        print(report())
        return 0
    if "--event" in argv:
        i = argv.index("--event")
        cov = load_coverage()
        for line in archive_event(argv[i + 1].upper(), argv[i + 2], opt("--source", "live"), cov, force="--force" in argv):
            print(line)
        save_coverage(cov)
        return 0
    if "--verify" in argv:
        i = argv.index("--verify")
        return verify(argv[i + 1].upper(), argv[i + 2])
    if "--report" in argv:
        print(report())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
