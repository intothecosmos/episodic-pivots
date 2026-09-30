"""outcomes.py — forward returns and a simulated rule-based trade for every candidate and Log note.

For each (ticker, date):
  day-1 bar, gap, forward returns from the day-1 OPEN at +1/+3/+5/+10/+20 sessions,
  max gain / max drawdown over 20 sessions, whether the day-1 low held,
  opening range (5-min, from yfinance when ≤60 days old; else daily approximation),
  simulated trade: entry ORH break, stop ORL, breakeven after a close ≥ entry + 1 ADR,
  exit on first close below 10/20/50-day SMA (three variants) or stop; R multiples.
Writes data/outcomes.csv (recomputed each run) and an "Outcome (auto)" block in each Log note.
Frontmatter keys appended at the bottom (never renamed): ret_5d, ret_20d, sim_r10, d1_low_held, hindsight.
"""
from __future__ import annotations

import datetime as dt
import re
import statistics as st
import sys
from pathlib import Path

from common import DATA, LOG, read_csv, upsert_csv, today_et, prev_trading_day
from data_sources import history, intraday_5m

OUTCOME_COLUMNS = [
    "ticker", "date", "trigger_date", "prev_close", "d1_open", "d1_high", "d1_low", "d1_close", "d1_vol",
    "gap_open_pct", "d1_open_to_close_pct", "record_day", "max_vol_252_prior",
    "ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "mfe_20d", "mae_20d", "d1_low_held",
    "or_basis", "orh", "orl", "trigger_fired", "sim_entry", "sim_stop", "sim_risk_pct",
    "sim_r10", "sim_exit10", "sim_days10", "sim_r20", "sim_exit20", "sim_days20", "sim_r50", "sim_exit50", "sim_days50",
    "sim_r_partial", "sim_open", "sessions_known", "computed_at",
]


def _sma(vals, n, i):
    if i + 1 < n:
        return None
    return sum(vals[i - n + 1:i + 1]) / n


def opening_range(ticker: str, day: str):
    df = intraday_5m(ticker)
    if df is None:
        return None
    try:
        import pandas as pd
        idx = df.index.tz_convert("America/New_York") if df.index.tz is not None else df.index
        mask = [(ts.strftime("%Y-%m-%d") == day) for ts in idx]
        d = df[mask]
        if len(d) == 0:
            return None
        first = d.iloc[0]
        orh, orl = float(first["High"]), float(first["Low"])
        later = d.iloc[1:]
        fired = bool((later["High"] > orh).any()) if len(later) else False
        # stop hit after trigger on day 1? (bars after the first bar that breaks ORH)
        stopped_d1 = False
        if fired:
            k = int((later["High"] > orh).values.argmax())
            after = later.iloc[k:]
            stopped_d1 = bool((after["Low"] < orl).any())
        return {"orh": orh, "orl": orl, "fired": fired, "stopped_d1": stopped_d1, "basis": "5-min bars"}
    except Exception:
        return None


def simulate(bars: list[dict], i: int, entry: float, stop: float, adr_pct: float, ma_n: int,
             stopped_d1: bool) -> dict:
    """bars oldest→newest; i = day-1 index. Returns r, exit_price, exit_date, days, open(bool)."""
    risk = entry - stop
    if risk <= 0:
        return {"r": None, "exit": None, "date": None, "days": None, "open": False}
    closes = [b["c"] for b in bars]
    if stopped_d1:
        return {"r": -1.0, "exit": stop, "date": bars[i]["d"], "days": 0, "open": False}
    cur_stop = stop
    be = False
    for j in range(i + 1, len(bars)):
        b = bars[j]
        if b["l"] <= cur_stop:               # stop first (conservative)
            return {"r": (cur_stop - entry) / risk, "exit": cur_stop, "date": b["d"], "days": j - i, "open": False}
        if not be and b["c"] >= entry * (1 + adr_pct / 100):
            cur_stop, be = entry, True       # breakeven after a close ≥ entry + 1 ADR
        ma = _sma(closes, ma_n, j)
        if ma is not None and b["c"] < ma and j - i >= 1:
            return {"r": (b["c"] - entry) / risk, "exit": b["c"], "date": b["d"], "days": j - i, "open": False}
    last = bars[-1]
    return {"r": (last["c"] - entry) / risk, "exit": last["c"], "date": last["d"], "days": len(bars) - 1 - i, "open": True}


def compute(ticker: str, date: str) -> dict | None:
    h = history(ticker, years=2)
    if not h:
        return None
    bars = h["rows"]
    ds = [b["d"] for b in bars]
    cand = [k for k, d in enumerate(ds) if d >= date]
    if not cand or cand[0] == 0:
        return None
    i = cand[0]
    b1, prev = bars[i], bars[i - 1]
    o = b1["o"]
    fut = bars[i + 1:i + 21]
    prior252 = bars[max(0, i - 252):i]
    w20 = [x for x in bars[max(0, i - 20):i] if x["l"]]
    adr_pct = 100 * st.mean(x["h"] / x["l"] - 1 for x in w20) if w20 else 5.0
    out = {c: None for c in OUTCOME_COLUMNS}
    out.update({"ticker": ticker, "date": date, "trigger_date": b1["d"], "prev_close": prev["c"],
                "d1_open": o, "d1_high": b1["h"], "d1_low": b1["l"], "d1_close": b1["c"], "d1_vol": b1["v"],
                "gap_open_pct": round((o / prev["c"] - 1) * 100, 2),
                "d1_open_to_close_pct": round((b1["c"] / o - 1) * 100, 2),
                "max_vol_252_prior": max((x["v"] for x in prior252), default=None),
                "sessions_known": len(fut), "computed_at": today_et().isoformat()})
    out["record_day"] = bool(out["max_vol_252_prior"] and b1["v"] >= out["max_vol_252_prior"])
    for n in (1, 3, 5, 10, 20):
        if i + n < len(bars):
            out[f"ret_{n}d"] = round((bars[i + n]["c"] / o - 1) * 100, 2)
    if fut:
        out["mfe_20d"] = round((max(x["h"] for x in fut) / o - 1) * 100, 2)
        out["mae_20d"] = round((min(x["l"] for x in fut) / o - 1) * 100, 2)
        out["d1_low_held"] = not any(x["l"] < b1["l"] for x in fut)
    # opening range
    orr = None
    if (today_et() - dt.date.fromisoformat(b1["d"])).days <= 58:
        orr = opening_range(ticker, b1["d"])
    if orr:
        out.update({"or_basis": orr["basis"], "orh": round(orr["orh"], 4), "orl": round(orr["orl"], 4),
                    "trigger_fired": orr["fired"]})
        entry, stop, stopped_d1 = orr["orh"], orr["orl"], orr["stopped_d1"]
        fired = orr["fired"]
    else:
        out.update({"or_basis": "daily approx (entry=open, stop=day-1 low)", "orh": o, "orl": b1["l"],
                    "trigger_fired": True})
        entry, stop, stopped_d1, fired = o, b1["l"], False, True
    if fired and entry > stop:
        out["sim_entry"], out["sim_stop"] = round(entry, 4), round(stop, 4)
        out["sim_risk_pct"] = round((entry - stop) / entry * 100, 2)
        for n in (10, 20, 50):
            s = simulate(bars, i, entry, stop, adr_pct, n, stopped_d1)
            out[f"sim_r{n}"] = None if s["r"] is None else round(s["r"], 2)
            out[f"sim_exit{n}"] = s["exit"]
            out[f"sim_days{n}"] = s["days"]
            if n == 10:
                out["sim_open"] = s["open"]
        # partial variant: 1/3 at day-3 close (if above entry), rest on 10-MA rule
        s10 = simulate(bars, i, entry, stop, adr_pct, 10, stopped_d1)
        if s10["r"] is not None and i + 3 < len(bars) and (s10["days"] or 0) >= 3:
            p = (bars[i + 3]["c"] - entry) / (entry - stop)
            out["sim_r_partial"] = round(p / 3 + s10["r"] * 2 / 3, 2)
        elif s10["r"] is not None:
            out["sim_r_partial"] = round(s10["r"], 2)
    return out


# ---------- Log notes ----------

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def note_targets() -> list[tuple[str, str, Path]]:
    out = []
    for p in sorted(LOG.glob("*.md")):
        m = FM_RE.match(p.read_text())
        if not m:
            continue
        fm = m.group(1)
        t = re.search(r"^ticker:\s*[\"']?([A-Za-z0-9.\-]+)", fm, re.M)   # tolerate quoted values
        d = re.search(r"^date:\s*[\"']?(\d{4}-\d\d-\d\d)", fm, re.M)
        if t and d:
            out.append((t.group(1).upper(), d.group(1), p))
    return out


def _set_fm_key(fm: str, key: str, val) -> str:
    v = "" if val is None else (str(val).lower() if isinstance(val, bool) else str(val))
    if re.search(rf"^{key}:", fm, re.M):
        return re.sub(rf"^{key}:.*$", f"{key}: {v}", fm, flags=re.M)
    return fm + f"\n{key}: {v}"


def update_note(p: Path, o: dict) -> None:
    txt = p.read_text()
    m = FM_RE.match(txt)
    if not m:
        return
    fm = m.group(1)
    for k in ("ret_5d", "ret_20d", "sim_r10", "d1_low_held"):
        fm = _set_fm_key(fm, k, o.get(k))
    body = txt[m.end():]
    held = o.get("d1_low_held")
    r20 = o.get("ret_20d")
    kind = "note" if r20 is None else "success" if r20 > 0 else "failure"   # unknown ≠ failure
    days = lambda n: "—" if o.get(f"sim_days{n}") is None else f"{o[f'sim_days{n}']}d"
    block = (
        "<!-- outcome:auto -->\n"
        f"> [!{kind}]- Outcome (auto, {o['computed_at']}) — from day-1 open {o['d1_open']:.2f} on {o['trigger_date']}\n"
        f"> +1d {_p(o['ret_1d'])} · +3d {_p(o['ret_3d'])} · +5d {_p(o['ret_5d'])} · +10d {_p(o['ret_10d'])} · +20d {_p(o['ret_20d'])} · "
        f"max gain {_p(o['mfe_20d'])} · max drawdown {_p(o['mae_20d'])} · day-1 low {'held' if held else 'broke' if held is False else '?'}"
        f" · {'record volume day' if o.get('record_day') else 'not a record day'}\n"
        f"> Simulated rule trade ({o.get('or_basis')}): entry {o.get('sim_entry')} · stop {o.get('sim_stop')} · "
        f"trigger {'fired' if o.get('trigger_fired') else 'never fired'} → 10-MA trail **{_r(o.get('sim_r10'))}** ({days(10)}) · "
        f"20-MA {_r(o.get('sim_r20'))} · 50-MA {_r(o.get('sim_r50'))} · 1/3-partial {_r(o.get('sim_r_partial'))}"
        f"{' · still open' if o.get('sim_open') else ''}\n"
        "<!-- /outcome:auto -->\n")
    # `\n?`: a note saved without a trailing newline must still be replaced (else silent no-op);
    # lambda: the replacement text is literal, never backslash-interpreted
    if "<!-- outcome:auto -->" in body:
        body = re.sub(r"<!-- outcome:auto -->.*?<!-- /outcome:auto -->\n?", lambda _: block, body, flags=re.S)
    else:
        body = body.rstrip("\n") + "\n\n" + block
    p.write_text(f"---\n{fm}\n---\n{body}")


def _p(x):
    return "—" if x is None else f"{x:+.1f}%"


def _r(x):
    return "—" if x is None else f"{x:+.2f}R"


def main(argv):
    targets = {}
    for t, d, p in note_targets():
        targets[(t, d)] = p
    for row in read_csv(DATA / "candidates.csv"):
        t, d = row.get("ticker"), row.get("date")
        if t and d and (t, d) not in targets:
            targets[(t, d)] = None
    only = [a for a in argv if not a.startswith("--")]
    rows = []
    for (t, d), p in sorted(targets.items(), key=lambda kv: kv[0][1]):
        if only and t not in only:
            continue
        if d >= today_et().isoformat():
            continue  # today's rows have no outcome yet
        o = compute(t, d)
        if not o:
            print(f"{t} {d}: no data")
            continue
        rows.append(o)
        if p is not None and "--no-notes" not in argv:
            update_note(p, o)
        print(f"{t} {d}: +5d {_p(o['ret_5d'])} +20d {_p(o['ret_20d'])} low-held {o['d1_low_held']} sim10 {_r(o['sim_r10'])} ({o['or_basis']})")
    n = upsert_csv(DATA / "outcomes.csv", rows, OUTCOME_COLUMNS, key=("ticker", "date"), overwrite=True)
    print(f"outcomes.csv: {len(rows)} rows computed, {n} new")


if __name__ == "__main__":
    main(sys.argv[1:])
