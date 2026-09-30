"""historical.py — Phase 2: build a historical EP-day database for hypothesis testing.

Universe: TradingView scanner — NYSE/NASDAQ/AMEX common stocks, cap ≥ $100M, price ≥ $0.50.
Bars: yfinance batched daily history (2y), consolidated volume; per-ticker fallback not attempted
here (speed) — tickers that fail are listed in data/historical_missing.txt.
Event: gap_open ≥ 8% vs prior close AND day volume ≥ 3× prior 30-day ADV AND ≥ 130 prior sessions
(so 6-month neglect is computable). One row per event with the same fields the live pipeline
records, plus forward returns and the simulated rule trade (daily approximation: entry = open,
stop = day-1 low). Catalyst proxy from SEC 8-K items filed within ±1 day (2.02 = earnings).

  python historical.py --fetch            # universe + bars → .cache/hist_bars.parquet (or .pkl)
  python historical.py --events           # detect events → data/historical_eps.csv
  python historical.py --sec              # add catalyst proxy from EDGAR (slow-ish, ~10 req/s)
  python historical.py --all
"""
from __future__ import annotations

import datetime as dt
import json
import pickle
import statistics as st
import sys
import time

from tradingview_screener import Query, col

from common import CACHE, DATA, get, SEC_UA, write_csv, read_csv

BARS_PKL = CACHE / "hist_bars.pkl"
EVENTS_CSV = DATA / "historical_eps.csv"
GAP_MIN, VOL_X, MIN_PRIOR = 8.0, 3.0, 130

EVENT_COLUMNS = [
    "ticker", "date", "exchange", "sector", "industry", "mkt_cap_m_now", "price_prev_close",
    "gap_open_pct", "d1_change_pct", "d1_open_to_close_pct", "d1_range_pct", "close_in_range",
    "vol_x_adv30", "record_vol_ratio", "prior_high_vol_days_180", "adr_pct",
    "ret_3m_pregap", "ret_6m_pregap", "base_tightness", "dist_52w_high_pct", "overhead_pct", "neglect_score",
    "ret_1d", "ret_3d", "ret_5d", "ret_10d", "ret_20d", "mfe_20d", "mae_20d", "d1_low_held",
    "sim_r10", "sim_days10", "sim_r20", "sim_days20", "sim_r50", "sim_days50", "sim_r_partial",
    "catalyst_proxy", "sec_items",
]


def universe() -> list[dict]:
    q = (Query().select("name", "exchange", "sector", "industry", "market_cap_basic", "close", "type", "subtype")
         .where(col("market_cap_basic") >= 100e6, col("close") >= 0.5,
                col("exchange").isin(["NASDAQ", "NYSE", "AMEX"]), col("type") == "stock",
                col("subtype").isin(["common", "foreign-issuer"]))
         .order_by("market_cap_basic", ascending=False).limit(6000).set_markets("america"))
    n, df = q.get_scanner_data()
    rows = []
    for _, r in df.iterrows():
        rows.append({"ticker": r["name"], "exchange": r["exchange"], "sector": r["sector"], "industry": r["industry"],
                     "mkt_cap_m_now": round(float(r["market_cap_basic"]) / 1e6, 1)})
    return rows


def fetch_bars(tickers: list[str], batch: int = 80) -> dict:
    import pandas as pd
    import yfinance as yf
    out = {}
    if BARS_PKL.exists():
        out = pickle.load(open(BARS_PKL, "rb"))
    todo = [t for t in tickers if t not in out]
    print(f"bars: {len(out)} cached, {len(todo)} to fetch")
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        ysyms = [t.replace(".", "-") for t in chunk]
        try:
            df = yf.download(ysyms, period="2y", interval="1d", group_by="ticker", threads=True,
                             progress=False, auto_adjust=False)
        except Exception as e:
            print("batch failed", i, e); time.sleep(5); continue
        for t, ys in zip(chunk, ysyms):
            try:
                # yfinance ≥0.2.5x returns MultiIndex columns even for one ticker; a symbol missing
                # from the batch raises KeyError here and is recorded as None (intended)
                sub = df[ys] if isinstance(df.columns, pd.MultiIndex) else df
                sub = sub.dropna(subset=["Close"])
                if len(sub) < 60:
                    out[t] = None; continue
                out[t] = [{"d": d.strftime("%Y-%m-%d"), "o": float(r["Open"]), "h": float(r["High"]),
                           "l": float(r["Low"]), "c": float(r["Close"]), "v": float(r["Volume"])} for d, r in sub.iterrows()]
            except Exception:
                out[t] = None
        pickle.dump(out, open(BARS_PKL, "wb"))
        print(f"  {min(i + batch, len(todo))}/{len(todo)}")
        time.sleep(1.0)
    return out


def _sma(vals, n, i):
    return None if i + 1 < n else sum(vals[i - n + 1:i + 1]) / n


def simulate(bars, i, entry, stop, adr_pct, ma_n):
    risk = entry - stop
    if risk <= 0:
        return None, None
    closes = [b["c"] for b in bars]
    if bars[i]["c"] < stop:                  # closed below the stop on day 1 → stopped
        return -1.0, 0
    cur, be = stop, False
    for j in range(i + 1, len(bars)):
        b = bars[j]
        if b["l"] <= cur:
            return round((cur - entry) / risk, 3), j - i
        if not be and b["c"] >= entry * (1 + adr_pct / 100):
            cur, be = entry, True
        ma = _sma(closes, ma_n, j)
        if ma is not None and b["c"] < ma:
            return round((b["c"] - entry) / risk, 3), j - i
    return None, None                        # still open at data end → excluded


def detect_events(bars_by_ticker: dict, meta: dict) -> list[dict]:
    events = []
    bad = []
    for t, bars in bars_by_ticker.items():
        if not bars:
            continue
        try:
            events += _events_for(t, bars, meta)
        except Exception as e:   # one ticker with junk bars (zero closes/lows) must not kill the whole build
            bad.append(f"{t}: {type(e).__name__}: {e}")
    if bad:
        print(f"  skipped {len(bad)} tickers with bad bars, e.g. {bad[:3]}")
    return events


def _events_for(t: str, bars: list[dict], meta: dict) -> list[dict]:
    events = []
    n = len(bars)
    for i in range(MIN_PRIOR, n - 21):   # need 20 forward sessions for a complete outcome
        b, p = bars[i], bars[i - 1]
        if p["c"] <= 0 or b["o"] <= 0:
            continue
        gap = (b["o"] / p["c"] - 1) * 100
        if gap < GAP_MIN:
            continue
        prior30 = bars[i - 30:i]
        adv = st.mean(x["v"] for x in prior30) or 0
        if adv <= 0 or b["v"] < VOL_X * adv:
            continue
        if p["c"] < 0.5:
            continue
        prior = bars[:i]
        w252 = prior[-252:]
        c = [x["c"] for x in prior]
        maxv = max(x["v"] for x in w252)
        w63 = c[-63:]
        med = st.median(w63)
        tight = sum(1 for x in w63 if abs(x / med - 1) <= 0.15) / len(w63)
        r3 = (c[-1] / c[-63] - 1) * 100
        r6 = (c[-1] / c[-126] - 1) * 100
        hi52 = max(x["h"] for x in w252)
        tot = sum(x["v"] for x in w252) or 1
        overhead = 100 * sum(x["v"] for x in w252 if x["c"] > b["o"]) / tot
        w20 = prior[-20:]
        adr = 100 * st.mean((x["h"] / x["l"] - 1) for x in w20 if x["l"] > 0)
        hv180 = sum(1 for x in prior[-180:] if x["v"] >= 3 * adv)
        s = 100.0
        if r3 > 30: s -= min(45.0, (r3 - 30) * 0.9)
        if r6 > 60: s -= min(30.0, (r6 - 60) * 0.4)
        if r3 < -40: s -= min(25.0, (-40 - r3) * 0.6)
        if r6 < -60: s -= 15.0
        s += (tight - 0.5) * 60
        neglect = max(0.0, min(100.0, s))
        fut = bars[i + 1:i + 21]
        o = b["o"]
        ev = {"ticker": t, "date": b["d"], **{k: meta.get(t, {}).get(k) for k in ("exchange", "sector", "industry", "mkt_cap_m_now")},
              "price_prev_close": round(p["c"], 4), "gap_open_pct": round(gap, 2),
              "d1_change_pct": round((b["c"] / p["c"] - 1) * 100, 2), "d1_open_to_close_pct": round((b["c"] / o - 1) * 100, 2),
              "d1_range_pct": round((b["h"] / b["l"] - 1) * 100, 2) if b["l"] else None,
              "close_in_range": round((b["c"] - b["l"]) / (b["h"] - b["l"]), 2) if b["h"] > b["l"] else None,
              "vol_x_adv30": round(b["v"] / adv, 2), "record_vol_ratio": round(b["v"] / maxv, 2) if maxv else None,
              "prior_high_vol_days_180": hv180, "adr_pct": round(adr, 2),
              "ret_3m_pregap": round(r3, 1), "ret_6m_pregap": round(r6, 1), "base_tightness": round(tight, 2),
              "dist_52w_high_pct": round((o / hi52 - 1) * 100, 1), "overhead_pct": round(overhead, 1), "neglect_score": round(neglect),
              "mfe_20d": round((max(x["h"] for x in fut) / o - 1) * 100, 2), "mae_20d": round((min(x["l"] for x in fut) / o - 1) * 100, 2),
              "d1_low_held": not any(x["l"] < b["l"] for x in fut)}
        for k in (1, 3, 5, 10, 20):
            ev[f"ret_{k}d"] = round((bars[i + k]["c"] / o - 1) * 100, 2)
        for m in (10, 20, 50):
            r, d = simulate(bars, i, o, b["l"], adr, m)
            ev[f"sim_r{m}"], ev[f"sim_days{m}"] = r, d
        r10 = ev["sim_r10"]
        if r10 is not None and (ev["sim_days10"] or 0) >= 3:
            pr = (bars[i + 3]["c"] - o) / (o - b["l"])
            ev["sim_r_partial"] = round(pr / 3 + r10 * 2 / 3, 3)
        else:
            ev["sim_r_partial"] = r10
        events.append(ev)
    return events


def _cik_map():
    j = get("https://www.sec.gov/files/company_tickers.json", ua=SEC_UA, json_out=True)
    return {v["ticker"].upper(): int(v["cik_str"]) for v in j.values()} if j else {}


def add_sec_proxy(events: list[dict]) -> None:
    cik = _cik_map()
    by_t = {}
    for e in events:
        by_t.setdefault(e["ticker"], []).append(e)
    done = 0
    for t, evs in by_t.items():
        c = cik.get(t.upper().replace(".", "-"))   # SEC lists class shares as BRK-B
        if not c:
            for e in evs: e["catalyst_proxy"] = "no-cik"
            continue
        j = get(f"https://data.sec.gov/submissions/CIK{c:010d}.json", ua=SEC_UA, json_out=True, sleep=0.12)
        rec = (j or {}).get("filings", {}).get("recent", {})
        filings = list(zip(rec.get("form", []), rec.get("filingDate", []), rec.get("items", [])))
        for e in evs:
            d = dt.date.fromisoformat(e["date"])
            lo, hi = (d - dt.timedelta(days=1)).isoformat(), (d + dt.timedelta(days=1)).isoformat()
            near = [(f, fd, it) for f, fd, it in filings if lo <= fd <= hi]
            items = ",".join(sorted({x for _, _, it in near for x in (it or "").split(",") if x}))
            forms = {f for f, _, _ in near}
            if "2.02" in items:
                e["catalyst_proxy"] = "earnings"
            elif "1.01" in items:
                e["catalyst_proxy"] = "agreement"
            elif "3.02" in items or any(f.startswith("424B") for f in forms):
                e["catalyst_proxy"] = "equity-sale"
            elif "8.01" in items or "7.01" in items:
                e["catalyst_proxy"] = "other-8k"
            elif near:
                e["catalyst_proxy"] = "filing-other"
            else:
                e["catalyst_proxy"] = "none"
            e["sec_items"] = items
        done += 1
        if done % 100 == 0:
            print(f"  sec {done}/{len(by_t)}")


def main(argv):
    do_all = "--all" in argv
    if do_all or "--fetch" in argv:
        uni = universe()
        json.dump(uni, open(CACHE / "universe.json", "w"))
        print(f"universe: {len(uni)}")
        fetch_bars([u["ticker"] for u in uni])
    if do_all or "--events" in argv:
        uni = json.load(open(CACHE / "universe.json"))
        meta = {u["ticker"]: u for u in uni}
        bars = pickle.load(open(BARS_PKL, "rb"))
        missing = [t for t, b in bars.items() if not b]
        (DATA / "historical_missing.txt").write_text("\n".join(missing))
        events = detect_events(bars, meta)
        print(f"events: {len(events)} across {len({e['ticker'] for e in events})} tickers · {len(missing)} tickers without bars")
        write_csv(EVENTS_CSV, events, EVENT_COLUMNS)
    if do_all or "--sec" in argv:
        events = read_csv(EVENTS_CSV)
        todo = [e for e in events if not e.get("catalyst_proxy")]
        print(f"sec proxy for {len(todo)} events")
        add_sec_proxy(todo)
        write_csv(EVENTS_CSV, events, EVENT_COLUMNS)


if __name__ == "__main__":
    main(sys.argv[1:])
