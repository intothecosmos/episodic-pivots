"""run_morning.py — orchestrate scan → gates → catalyst → brief.

  python run_morning.py                 # premarket mode, label v1 (07:45)
  python run_morning.py --label v2      # 09:10 refresh
  python run_morning.py --mode regular  # after the open / evening dry run
  python run_morning.py --no-freeze     # don't write candidates.csv (testing)
  python run_morning.py --date 2026-09-29   # override the as-of date (backfill / dry run)

Exits quietly on non-trading days.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from common import BRIEFS, is_trading_day, today_et
from scan import scan, regime
from gates import score_all
from catalyst import gather
from brief import build


def main(argv):
    mode = argv[argv.index("--mode") + 1] if "--mode" in argv else "premarket"
    label = argv[argv.index("--label") + 1] if "--label" in argv else "v1"
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 40
    asof = dt.date.fromisoformat(argv[argv.index("--date") + 1]) if "--date" in argv else today_et()
    freeze = "--no-freeze" not in argv
    if not is_trading_day(asof) and "--force" not in argv:
        print(f"{asof} is not a trading day — nothing to do.")
        return 0
    reg = regime()
    rows = scan(mode, limit)
    print(f"regime {reg.get('gate0')} · {len(rows)} hits ({mode})")
    cands = score_all(rows, reg, asof, freeze=freeze)
    cats = {}
    for c in cands:
        t = c.get("ticker")
        if not t:
            continue
        try:
            cats[t] = gather(t, c.get("description"))
        except Exception as e:
            cats[t] = {"pre_tier": "unknown", "headlines": [], "filings": [], "pre_tier_hits": [f"catalyst error {e}"]}
    (BRIEFS / f"{asof.isoformat()}.catalysts.json").write_text(json.dumps(cats, indent=1))
    text, watch = build(asof.isoformat(), cands, cats, reg, label=label)
    print(f"brief written: Briefs/{asof.isoformat()}.md · watchlist: {watch}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
