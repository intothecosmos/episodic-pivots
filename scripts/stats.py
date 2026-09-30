"""stats.py — bucket statistics for EP hypothesis testing. Used by the historical baseline review
and the weekly review. Reads data/historical_eps.csv (and optionally the live candidates/outcomes).

  python stats.py                      # prints the markdown report for the historical set
  python stats.py --out Reviews/x.md   # writes it
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

from common import DATA, REVIEWS, read_csv, today_et


def _f(x):
    try:
        return None if x in (None, "", "None") else float(x)
    except Exception:
        return None


def _fmt(x, nd=2, suf=""):
    return "—" if x is None else f"{x:+.{nd}f}{suf}"


def summarize(rows: list[dict], label: str) -> list:
    n = len(rows)
    if n == 0:
        return [label, 0, "—", "—", "—", "—", "—", "—"]
    r20 = [v for v in (_f(r.get("ret_20d")) for r in rows) if v is not None]
    held = [r for r in rows if str(r.get("gap_held")) == "True"]
    s10 = [v for v in (_f(r.get("sim_r10")) for r in held) if v is not None]
    low = [str(r.get("d1_low_held")) == "True" for r in rows if r.get("d1_low_held") not in (None, "", "None")]
    return [label, n,
            _fmt(st.mean(r20), 1, "%") if r20 else "—",
            _fmt(st.median(r20), 1, "%") if r20 else "—",
            f"{100 * sum(low) / len(low):.0f}%" if low else "—",
            f"{len(s10)}",
            _fmt(st.mean(s10)) if s10 else "—",
            f"{100 * sum(v > 0 for v in s10) / len(s10):.0f}%" if s10 else "—"]


HEADER = "| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |\n| --- | --- | --- | --- | --- | --- | --- | --- |"


def bucket_table(rows, key, edges, labels, title) -> str:
    lines = [f"### {title}", "", HEADER]
    for lo, hi, lab in zip(edges[:-1], edges[1:], labels):
        sub = [r for r in rows if (v := _f(r.get(key))) is not None and lo <= v < hi]
        lines.append("| " + " | ".join(str(x) for x in summarize(sub, lab)) + " |")
    return "\n".join(lines) + "\n"


def cat_table(rows, key, title, order=None) -> str:
    vals = order or sorted({str(r.get(key)) for r in rows})
    lines = [f"### {title}", "", HEADER]
    for v in vals:
        sub = [r for r in rows if str(r.get(key)) == v]
        if sub:
            lines.append("| " + " | ".join(str(x) for x in summarize(sub, v)) + " |")
    return "\n".join(lines) + "\n"


INF = float("inf")


def report(rows: list[dict], title: str) -> str:
    out = [f"# {title}", "",
           f"Generated {today_et().isoformat()} from {len(rows)} EP-days ({len({r['ticker'] for r in rows})} tickers). "
           "Event = open gap ≥ 8% vs prior close AND day volume ≥ 3× prior 30-day ADV, price ≥ $0.50, cap ≥ $100M today. "
           "Returns are from the day-1 open. The simulated trade enters at the day-1 close only when the gap held "
           "(close > open), stops at the day-1 low, moves to breakeven after a close ≥ entry + 1 ADR, and exits on the first "
           "close below the 10-day SMA. n is shown everywhere; nothing with n < 30 is a conclusion.", ""]
    out.append("## Baseline\n\n" + HEADER + "\n| " + " | ".join(str(x) for x in summarize(rows, "all EP-days")) + " |\n")
    held = [r for r in rows if str(r.get("gap_held")) == "True"]
    out.append("| " + " | ".join(str(x) for x in summarize(held, "gap held (close > open)")) + " |\n")
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if str(r.get('gap_held')) != 'True'], "gap faded (close ≤ open)")) + " |\n")
    # exit variants on the held subset
    out.append("### Exit variants (gap-held trades)\n\n| Variant | n | avg R | median R | win % | p90 R |\n| --- | --- | --- | --- | --- | --- |")
    for k, lab in (("sim_r10", "10-day SMA close trail"), ("sim_r20", "20-day"), ("sim_r50", "50-day"), ("sim_r_partial", "1/3 at day-3 close + 10-day trail")):
        s = sorted(v for v in (_f(r.get(k)) for r in held) if v is not None)
        if s:
            out.append(f"| {lab} | {len(s)} | {_fmt(st.mean(s))} | {_fmt(st.median(s))} | {100*sum(v>0 for v in s)/len(s):.0f}% | {_fmt(s[int(0.9*len(s))])} |")
    out.append("")
    out.append(bucket_table(rows, "gap_open_pct", [8, 12, 20, 40, INF], ["8–12%", "12–20%", "20–40%", "40%+"], "Gap size"))
    out.append(bucket_table(rows, "vol_x_adv30", [3, 5, 10, 20, INF], ["3–5×", "5–10×", "10–20×", "20×+"], "Volume ÷ 30-day ADV (Kullamägi ratio, full day)"))
    out.append(bucket_table(rows, "record_vol_ratio", [0, 0.5, 1, INF], ["<0.5× of 252-day max", "0.5–1×", "≥1× (record day)"], "Record-volume test (rubric Gate 3 strong pass)"))
    out.append(bucket_table(rows, "neglect_score", [0, 60, 85, 101], ["<60 (chart fail)", "60–85", "85–100"], "Neglect score (rubric Gate 2 pass line = 60)"))
    out.append(bucket_table(rows, "ret_3m_pregap", [-INF, -30, 0, 30, 100, INF], ["< −30%", "−30–0%", "0–30%", "30–100% (extended)", "100%+"], "3-month pre-gap return"))
    out.append(bucket_table(rows, "overhead_pct", [0, 20, 50, 80, 101], ["<20% (open air)", "20–50%", "50–80%", "80%+"], "Overhead supply (hypothesis: not enforced)"))
    out.append(bucket_table(rows, "dist_52w_high_pct", [-INF, -50, -25, -5, INF], ["< −50% from high", "−50–−25%", "−25–−5%", "within 5% / new high"], "Distance from 52-week high at the open"))
    out.append(bucket_table(rows, "adr_pct", [0, 4, 8, INF], ["<4%", "4–8%", "8%+"], "ADR (20-day) — theStrat Lab found ≥4% helps"))
    out.append(bucket_table(rows, "prior_high_vol_days_180", [0, 5, INF], ["0–4", "5+"], "Prior high-volume days (≥3× ADV) in 180 sessions"))
    out.append(bucket_table(rows, "close_in_range", [0, 0.5, 0.8, 1.01], ["bottom half", "0.5–0.8", "top 20%"], "Day-1 close position in range"))
    out.append(bucket_table(rows, "mkt_cap_m_now", [100, 300, 1000, 10000, INF], ["$100–300M", "$300M–1B", "$1–10B", "$10B+"], "Market cap (today's, proxy)"))
    if any(r.get("catalyst_proxy") for r in rows):
        out.append(cat_table(rows, "catalyst_proxy", "Catalyst proxy from SEC filings within ±1 day", ["earnings", "agreement", "other-8k", "filing-other", "equity-sale", "none", "no-cik"]))
    # rubric v2 machine screen
    def passes(r):
        return (_f(r.get("neglect_score")) or 0) >= 60 and (_f(r.get("vol_x_adv30")) or 0) >= 1
    def strong(r):
        return passes(r) and ((_f(r.get("vol_x_adv30")) or 0) >= 10 or (_f(r.get("record_vol_ratio")) or 0) >= 1)
    out.append("### Rubric v2 machine gates (chart pass ∧ volume pass; strong = ≥10× ADV or record day)\n\n" + HEADER)
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if not passes(r)], "fails a gate")) + " |")
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if passes(r)], "passes")) + " |")
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if strong(r)], "passes + strong volume")) + " |")
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if strong(r) and (_f(r.get('overhead_pct')) or 100) < 20], "strong + open air (<20% overhead)")) + " |")
    out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if strong(r) and str(r.get('catalyst_proxy')) == 'earnings'], "strong + earnings 8-K")) + " |")
    out.append("")
    return "\n".join(out)


def live_report(weeks: int = 1) -> str:
    """Weekly section from the live pipeline: candidates + outcomes + Log decisions."""
    import datetime as dt
    cands = read_csv(DATA / "candidates.csv")
    outs = {(r["ticker"], r["date"]): r for r in read_csv(DATA / "outcomes.csv")}
    cutoff = (today_et() - dt.timedelta(days=7 * weeks)).isoformat()
    seen, rows = set(), []
    for c in cands:
        k = (c.get("ticker"), c.get("date"))
        if not c.get("ticker") or c.get("date", "") < cutoff or k in seen:
            continue
        seen.add(k)
        o = outs.get(k, {})
        rows.append({**c, **{kk: o.get(kk) for kk in ("ret_5d", "ret_20d", "d1_low_held", "sim_r10", "trigger_fired")},
                     "gap_held": (o.get("d1_open_to_close_pct") not in (None, "", "None")) and float(o.get("d1_open_to_close_pct") or 0) > 0,
                     "vol_x_adv30": c.get("kq_vol_ratio")})
    out = [f"## Live pipeline — last {weeks} week(s)", "",
           f"{len(rows)} candidate-days · {sum(1 for r in rows if r.get('ret_5d') not in (None,'','None'))} with +5d outcomes · "
           f"{sum(1 for r in rows if r.get('ret_20d') not in (None,'','None'))} with +20d outcomes", ""]
    if rows:
        out.append(HEADER)
        out.append("| " + " | ".join(str(x) for x in summarize(rows, "all candidates")) + " |")
        for g in ("strong", "pass", "fail"):
            out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if r.get("gate_volume_auto") == g], f"volume {g}")) + " |")
        for g in ("pass", "fail"):
            out.append("| " + " | ".join(str(x) for x in summarize([r for r in rows if r.get("gate_chart_auto") == g], f"chart {g}")) + " |")
        out.append("")
    # decisions from Log notes
    import re
    FM = re.compile(r"^---\n(.*?)\n---\n", re.S)
    from common import LOG
    dec = []
    for p in sorted(LOG.glob("*.md")):
        m = FM.match(p.read_text())
        if not m:
            continue
        d = {}
        for line in m.group(1).splitlines():
            mm = re.match(r"^([A-Za-z_]\w*):\s*(.*?)\s*(#.*)?$", line)
            if mm:
                d[mm.group(1)] = mm.group(2).strip().strip('"')
        if d.get("type") == "ep-eval" and d.get("date", "") >= cutoff:
            dec.append(d)
    out.append(f"Matt's evaluations this period: {len(dec)} · taken: {sum(1 for d in dec if d.get('taken') == 'true')} · "
               f"hindsight-flagged: {sum(1 for d in dec if d.get('hindsight') == 'true')}")
    for d in dec:
        out.append(f"- {d.get('date')} {d.get('ticker')} — {d.get('grade')}★ {d.get('verdict')} · status {d.get('status')} · +5d {d.get('ret_5d') or '—'} · +20d {d.get('ret_20d') or '—'} · sim R {d.get('sim_r10') or '—'}")
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    rows = read_csv(DATA / "historical_eps.csv")
    if "--live" in sys.argv:
        text = live_report(int(sys.argv[sys.argv.index("--weeks") + 1]) if "--weeks" in sys.argv else 1)
    else:
        text = report(rows, "Historical EP baseline")
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(text)
    else:
        print(text)
