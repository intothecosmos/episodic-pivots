"""scan.py — pull EP candidates from the TradingView scanner and the market regime.

Modes
  premarket : premarket_change >= GAP_MIN and premarket_volume >= PM_VOL_X * ADV30
  regular   : gap (open vs prior close) or change >= GAP_MIN and relative volume >= RVOL_MIN
              (used after 09:30 and for evening dry runs)

Output: list of dict rows with the scanner fields we need, plus a regime dict.
CLI: python scan.py [premarket|regular] [--limit N] → prints JSON.
"""
from __future__ import annotations

import json
import sys

from tradingview_screener import Query, col

from common import now_et
from data_sources import history

GAP_MIN = 8.0          # % — rubric v2 screen
PM_VOL_X = 0.5         # premarket volume ≥ 0.5 × ADV30
RVOL_MIN = 3.0         # regular-session fallback
CAP_MIN = 100e6
PRICE_MIN = 0.5
EXCHANGES = ["NASDAQ", "NYSE", "AMEX"]

COLUMNS = [
    "name", "description", "exchange", "type", "subtype", "sector", "industry",
    "close", "open", "high", "low", "volume", "change", "gap", "change_from_open",
    "premarket_change", "premarket_volume", "premarket_close", "premarket_high", "premarket_low",
    "relative_volume_10d_calc", "relative_volume_intraday|5",
    "average_volume_10d_calc", "average_volume_30d_calc", "average_volume_90d_calc",
    "market_cap_basic", "float_shares_outstanding_current", "total_shares_outstanding",
    "price_52_week_high", "price_52_week_low", "High.All", "High.6M", "High.3M",
    "SMA10", "SMA20", "SMA50", "SMA200", "ATR", "ADR", "Volatility.D",
    "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.Y",
    "earnings_release_date", "earnings_release_next_date",
    "eps_surprise_percent_fq", "revenue_surprise_percent_fq",
    "earnings_per_share_diluted_yoy_growth_fq", "total_revenue_yoy_growth_fq",
    "Value.Traded", "beta_1_year",
]


def _base_conds():
    return [col("market_cap_basic") >= CAP_MIN,
            col("close") >= PRICE_MIN,
            col("exchange").isin(EXCHANGES),
            col("type") == "stock",
            col("subtype").isin(["common", "foreign-issuer"])]


def scan(mode: str = "premarket", limit: int = 60) -> list[dict]:
    # NB: Query.where() REPLACES the filter list on each call — pass all conditions at once.
    if mode == "premarket":
        conds = _base_conds() + [col("premarket_change") >= GAP_MIN,
                                 col("premarket_volume") >= 50_000]
        order = "premarket_change"
    else:
        conds = _base_conds() + [col("change") >= GAP_MIN,
                                 col("relative_volume_10d_calc") >= RVOL_MIN]
        order = "change"
    q = (Query().select(*COLUMNS).where(*conds).order_by(order, ascending=False)
         .set_markets("america"))
    n, df = q.limit(limit).get_scanner_data()
    rows = []
    for _, r in df.iterrows():
        d = {k: (None if (v is None or (isinstance(v, float) and v != v)) else v)
             for k, v in r.to_dict().items()}
        d["ticker"] = d.get("name")
        d["symbol"] = d.get("ticker")  # "NASDAQ:XYZ" from the package
        if mode == "premarket":
            adv = d.get("average_volume_30d_calc") or 0
            pmv = d.get("premarket_volume") or 0
            d["pm_vol_x_adv"] = round(pmv / adv, 2) if adv else None
            if adv and pmv < PM_VOL_X * adv:
                d["screen_note"] = f"premarket volume {d['pm_vol_x_adv']}x ADV < {PM_VOL_X}x"
        d["scan_mode"] = mode
        d["snapshot_et"] = now_et().strftime("%Y-%m-%d %H:%M")
        rows.append(d)
    return rows


def regime() -> dict:
    """Gate 0: QQQ 10-day SMA > 20-day SMA, both rising (vs 3 sessions ago). Also SPY."""
    out = {}
    for t in ("QQQ", "SPY"):
        h = history(t)
        if not h:
            out[t] = {"state": "unknown"}
            continue
        c = [r["c"] for r in h["rows"]]
        if len(c) < 25:
            out[t] = {"state": "unknown"}
            continue
        sma = lambda n, off=0: sum(c[len(c) - n - off:len(c) - off]) / n
        s10, s20, s10p, s20p = sma(10), sma(20), sma(10, 3), sma(20, 3)
        green = s10 > s20 and s10 > s10p and s20 > s20p
        out[t] = {"state": "green" if green else "red", "close": c[-1], "sma10": round(s10, 2),
                  "sma20": round(s20, 2), "sma10_rising": s10 > s10p, "sma20_rising": s20 > s20p,
                  "asof": h["rows"][-1]["d"]}
    q = out.get("QQQ", {})
    out["gate0"] = q.get("state", "unknown")
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "premarket"
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 60
    print(json.dumps({"regime": regime(), "rows": scan(mode, limit)}, indent=1, default=str))
