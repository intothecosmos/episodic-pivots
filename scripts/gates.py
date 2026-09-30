"""gates.py — machine gate scoring for scanner hits. Appends FROZEN rows to data/candidates.csv.

For each hit we compute, with a stated basis:
  kq_vol_ratio       volume so far ÷ 30-day ADV          (Kullamägi's rule; ≥1 pass, ≥10 strong)
  record_vol_ratio   volume so far ÷ largest day in prior 252 sessions (≥1 = record day)
  neglect_score      0–100 from pre-gap 3m/6m return, base tightness, distance to 52-wk high
  overhead_pct       volume-weighted share of prior 252 sessions that closed above current price
  adr_pct            20-day average daily range %
  dollar_vol_proj    projected full-day dollar volume
  event_risk         next confirmed/estimated earnings inside 14 sessions
  gate_*_auto        pass/fail/strong per rubric v2 (chart gate uses neglect only; overhead is logged)
Grades are NOT assigned here — brief.py does that once the catalyst tier is known.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import statistics as st
import sys

from common import DATA, now_et, today_et, upsert_csv, next_trading_day
from data_sources import history, earnings, next_earnings, last_earnings

CANDIDATE_COLUMNS = [
    "symbol", "ticker", "exchange", "date", "snapshot_et", "scan_mode", "frozen_at",
    "description", "sector", "industry",
    "price", "prev_close", "gap_pct", "gap_basis", "change_pct", "premarket_volume", "volume",
    "adv30", "adv10", "kq_vol_ratio", "kq_vol_ratio_basis",
    "max_vol_252", "max_vol_252_date", "record_vol_ratio", "record_vol_ratio_basis",
    "market_cap_m", "float_m", "shares_out_m", "dollar_vol_proj_m",
    "ret_3m_pregap", "ret_6m_pregap", "base_tightness", "dist_52w_high_pct", "dist_ath_pct",
    "neglect_score", "overhead_pct", "adr_pct", "atr",
    "sma10", "sma20", "sma50", "sma200",
    "last_earnings_date", "days_since_earnings", "next_earnings_date", "next_earnings_confirmed",
    "event_risk", "eps_surprise_pct", "rev_surprise_pct", "eps_yoy_growth_pct", "rev_yoy_growth_pct",
    "gate_volume_auto", "gate_chart_auto", "gate_tradability_auto", "tradability_flags",
    "regime_qqq", "regime_spy", "hist_src", "notes",
]


def _f(x, nd=2):
    try:
        return None if x is None else round(float(x), nd)
    except Exception:
        return None


def score_row(r: dict, regime: dict, asof: dt.date | None = None) -> dict:
    asof = asof or today_et()
    t = r["ticker"]
    out = {c: None for c in CANDIDATE_COLUMNS}
    out.update({
        "symbol": r.get("symbol"), "ticker": t, "exchange": r.get("exchange"),
        "date": asof.isoformat(), "snapshot_et": r.get("snapshot_et"), "scan_mode": r.get("scan_mode"),
        "frozen_at": now_et().strftime("%Y-%m-%d %H:%M"),
        "description": r.get("description"), "sector": r.get("sector"), "industry": r.get("industry"),
        "market_cap_m": _f((r.get("market_cap_basic") or 0) / 1e6, 1),
        "float_m": _f((r.get("float_shares_outstanding_current") or 0) / 1e6, 2) or None,
        "shares_out_m": _f((r.get("total_shares_outstanding") or 0) / 1e6, 2) or None,
        "adv30": _f(r.get("average_volume_30d_calc"), 0), "adv10": _f(r.get("average_volume_10d_calc"), 0),
        "premarket_volume": _f(r.get("premarket_volume"), 0), "volume": _f(r.get("volume"), 0),
        "sma10": _f(r.get("SMA10")), "sma20": _f(r.get("SMA20")), "sma50": _f(r.get("SMA50")),
        "sma200": _f(r.get("SMA200")), "atr": _f(r.get("ATR"), 3),
        "eps_surprise_pct": _f(r.get("eps_surprise_percent_fq"), 1),
        "rev_surprise_pct": _f(r.get("revenue_surprise_percent_fq"), 1),
        "eps_yoy_growth_pct": _f(r.get("earnings_per_share_diluted_yoy_growth_fq"), 1),
        "rev_yoy_growth_pct": _f(r.get("total_revenue_yoy_growth_fq"), 1),
        "regime_qqq": regime.get("QQQ", {}).get("state"), "regime_spy": regime.get("SPY", {}).get("state"),
    })
    notes = []

    # --- price / gap ---
    pm = r.get("scan_mode") == "premarket"
    price = r.get("premarket_close") if pm and r.get("premarket_close") else r.get("close")
    out["price"] = _f(price, 4)
    if pm:
        out["gap_pct"] = _f(r.get("premarket_change"), 2); out["gap_basis"] = "premarket vs prior close"
    else:
        out["gap_pct"] = _f(r.get("gap"), 2); out["gap_basis"] = "open vs prior close"
    out["change_pct"] = _f(r.get("change"), 2)

    # --- history-based fields ---
    h = history(t)
    rows = h["rows"] if h else []
    out["hist_src"] = h["src"] if h else None
    # prior sessions only: drop today's bar if present
    prior = [x for x in rows if x["d"] < asof.isoformat()]
    if prior:
        out["prev_close"] = _f(prior[-1]["c"], 4)
        w252 = prior[-252:]
        mv = max(w252, key=lambda x: x["v"])
        out["max_vol_252"], out["max_vol_252_date"] = _f(mv["v"], 0), mv["d"]
        c = [x["c"] for x in prior]
        if len(c) > 130:
            out["ret_3m_pregap"] = _f((c[-1] / c[-63] - 1) * 100, 1) if c[-63] else None
            out["ret_6m_pregap"] = _f((c[-1] / c[-126] - 1) * 100, 1) if c[-126] else None
        elif len(c) > 65:
            out["ret_3m_pregap"] = _f((c[-1] / c[-63] - 1) * 100, 1) if c[-63] else None
        w63 = c[-63:]
        med = st.median(w63)
        if med:
            out["base_tightness"] = _f(sum(1 for x in w63 if abs(x / med - 1) <= 0.15) / len(w63), 2)
        hi52 = max(x["h"] for x in w252)
        out["dist_52w_high_pct"] = _f((float(price) / hi52 - 1) * 100, 1) if price else None
        ath = r.get("High.All")
        out["dist_ath_pct"] = _f((float(price) / float(ath) - 1) * 100, 1) if (price and ath) else None
        # overhead: volume-weighted share of prior 252 sessions closing above current price
        tot = sum(x["v"] for x in w252) or 1
        out["overhead_pct"] = _f(100 * sum(x["v"] for x in w252 if x["c"] > float(price)) / tot, 1) if price else None
        w20 = [x for x in prior[-20:] if x["l"]]
        out["adr_pct"] = _f(100 * st.mean(x["h"] / x["l"] - 1 for x in w20), 2) if w20 else None
        # neglect score: 100 = quiet base; extension and collapse both cost points
        s = 100.0
        r3 = out["ret_3m_pregap"] or 0.0
        r6 = out["ret_6m_pregap"] if out["ret_6m_pregap"] is not None else r3
        if r3 > 30:
            s -= min(45.0, (r3 - 30) * 0.9)          # extended into the gap
        if r6 > 60:
            s -= min(30.0, (r6 - 60) * 0.4)
        if r3 < -40:
            s -= min(25.0, (-40 - r3) * 0.6)         # collapsing, not basing
        if r6 < -60:
            s -= 15.0
        s += ((out["base_tightness"] or 0.5) - 0.5) * 60   # ±30 for tightness
        out["neglect_score"] = _f(max(0.0, min(100.0, s)), 0)
    else:
        notes.append("no history — neglect/record-volume not computed")

    # --- volume ratios ---
    adv = out["adv30"] or 0
    if pm:
        vol_so_far, basis = (out["premarket_volume"] or 0), "premarket"
    else:
        vol_so_far, basis = (out["volume"] or 0), ("fullday" if now_et().hour >= 16 else f"intraday {now_et().strftime('%H:%M')} ET")
    out["kq_vol_ratio"] = _f(vol_so_far / adv, 2) if adv else None
    out["kq_vol_ratio_basis"] = basis
    if out["max_vol_252"]:
        out["record_vol_ratio"] = _f(vol_so_far / out["max_vol_252"], 2)
        out["record_vol_ratio_basis"] = basis
    out["dollar_vol_proj_m"] = _f(vol_so_far * float(price or 0) / 1e6 * (3.0 if pm else 1.0), 1)
    if pm:
        notes.append("dollar volume projected = 3× premarket")

    # --- events ---
    le = last_earnings(t, asof)
    if le:
        out["last_earnings_date"] = le["date"]
        out["days_since_earnings"] = (asof - dt.date.fromisoformat(le["date"])).days
    ne = next_earnings(t, asof)
    # a report scheduled for TODAY after the close is still ahead of the trade (binary inside the window)
    today_amc = [x for x in (earnings(t) or []) if x["date"] == asof.isoformat() and (x.get("time") or "") >= "15:00"]
    if today_amc:
        ne = today_amc[0]
    if ne:
        out["next_earnings_date"], out["next_earnings_confirmed"] = ne["date"], ne["confirmed"]
        d = dt.date.fromisoformat(ne["date"])
        if (d - asof).days <= 20:
            out["event_risk"] = f"earnings {ne['date']}{' AMC today' if today_amc else ''}{'' if ne['confirmed'] else ' (est)'}"

    # --- auto gates ---
    kq = out["kq_vol_ratio"] or 0
    rec = out["record_vol_ratio"] or 0
    if pm:
        out["gate_volume_auto"] = "strong" if (kq >= 5 or rec >= 1) else "pass" if kq >= 0.5 else "fail"
    else:
        out["gate_volume_auto"] = "strong" if (kq >= 10 or rec >= 1) else "pass" if kq >= 1 else "fail"
    ns = out["neglect_score"]
    out["gate_chart_auto"] = None if ns is None else ("pass" if ns >= 60 else "fail")
    flags = []
    if (out["float_m"] or 99) < 1:
        flags.append("float<1M")
    if (out["market_cap_m"] or 0) < 100:
        flags.append("cap<100M")
    if (out["price"] or 0) < 0.5:
        flags.append("price<0.50")
    if (out["dollar_vol_proj_m"] or 0) < 10:
        flags.append("dollar-vol<10M(proj)")
    if re.search(r"acquisition corp|spac\b|blank check", str(r.get("description") or ""), re.I):
        flags.append("SPAC")
    out["tradability_flags"] = ";".join(flags)
    out["gate_tradability_auto"] = "fail" if flags else "pass"
    out["notes"] = "; ".join(notes)
    return out


def score_all(rows: list[dict], regime: dict, asof: dt.date | None = None, freeze: bool = True) -> list[dict]:
    scored = []
    for r in rows:
        try:
            scored.append(score_row(r, regime, asof))
        except Exception as e:  # never let one ticker kill the run
            scored.append({"symbol": r.get("symbol"), "ticker": r.get("ticker"), "exchange": r.get("exchange"),
                           "description": r.get("description"), "snapshot_et": r.get("snapshot_et"),
                           "scan_mode": r.get("scan_mode"), "date": (asof or today_et()).isoformat(),
                           "notes": f"score error: {type(e).__name__}: {e}"})
    if freeze:
        upsert_csv(DATA / "candidates.csv", scored, CANDIDATE_COLUMNS,
                   key=("symbol", "date", "snapshot_et"), overwrite=False)
    return scored


if __name__ == "__main__":
    from scan import scan, regime as _regime
    mode = sys.argv[1] if len(sys.argv) > 1 else "premarket"
    reg = _regime()
    rows = scan(mode, 25)
    out = score_all(rows, reg, freeze="--freeze" in sys.argv)
    keys = ["symbol", "price", "gap_pct", "kq_vol_ratio", "record_vol_ratio", "neglect_score",
            "overhead_pct", "adr_pct", "dollar_vol_proj_m", "event_risk",
            "gate_volume_auto", "gate_chart_auto", "gate_tradability_auto", "tradability_flags"]
    for o in out:
        print({k: o.get(k) for k in keys})
