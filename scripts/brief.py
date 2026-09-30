"""brief.py — turn scored candidates + catalyst evidence into the morning brief.

Auto grade (machine, provisional — the run's Claude pass or Matt confirms the tier):
  Gate 4 fail → 1★ NO TRADE.  Tier C / cash-takeover target → 1★ NO TRADE.
  Base: Tier A 4★, Tier B 3★, Unknown 3★ (cap).  +1 if volume strong AND chart pass (max 5).
  −1 chart fail.  Volume fail → max 2★.  Event inside window → verdict WATCH (event-capped).
  Regime red → verdict note "regime red: half size / skip".
Writes Briefs/YYYY-MM-DD.md (v1 or v2 by run label) and Briefs/watchlist-YYYY-MM-DD.txt.
"""
from __future__ import annotations

import json
from pathlib import Path

from common import BRIEFS, fmt, now_et

STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}


def auto_grade(c: dict, cat: dict) -> dict:
    pre = cat.get("pre_tier", "unknown")
    tier = {"A?": "A", "B?": "B", "C?": "C", "MA-target": "MA", "unknown": "unknown"}.get(pre, "unknown")
    g4 = c.get("gate_tradability_auto")
    gv, gc = c.get("gate_volume_auto"), c.get("gate_chart_auto")
    why = []
    if g4 is None:  # gates never computed (score error) — an uncomputed gate is not a pass
        grade, verdict = 1, "NO DATA"; why.append(f"gates not computed ({c.get('notes') or 'score error'})")
    elif g4 == "fail":
        grade, verdict = 1, "NO TRADE"; why.append(f"Gate 4 fail ({c.get('tradability_flags')})")
    elif tier == "MA":
        grade, verdict = 1, "NO TRADE"; why.append("cash takeover target — upside capped, not an EP")
    elif tier == "C":
        grade, verdict = 1, "NO TRADE"; why.append("Tier C catalyst (offering/promo/sympathy)")
    else:
        grade = {"A": 4, "B": 3, "unknown": 3}[tier]
        if gv == "strong" and gc == "pass":
            grade = min(5, grade + 1)
        if gc == "fail":
            grade = min(grade - 1, 2); why.append(f"chart fail: neglect {c.get('neglect_score')} (extended/collapsed pre-gap)")
        if gv == "fail":
            grade = min(grade, 2); why.append(f"volume: {c.get('kq_vol_ratio')}x ADV ({c.get('kq_vol_ratio_basis')})")
        if tier == "unknown":
            grade = min(grade, 3); why.append("catalyst unknown — capped 3★, recheck")
        if gc is None:  # no daily history → chart gate unjudged; never let it pass by absence
            grade = min(grade, 3); why.append("chart gate not computed (no history) — read the chart by hand")
        grade = max(1, grade)
        verdict = "TRADE" if grade >= 4 else "TRADE small / WATCH" if grade == 3 else "NO TRADE"
        if gc is None and grade >= 3:
            verdict = "WATCH (chart unjudged)"
        if c.get("event_risk") and grade >= 3:
            verdict = "WATCH (event-capped)"; why.append(f"event: {c['event_risk']}")
        # 40%+ gaps were the worst historical band (n=209): WATCH unless Tier A with strong volume
        gp = c.get("gap_pct")
        try:
            gp = float(gp) if gp not in (None, "") else None
        except Exception:
            gp = None
        if gp is not None and gp >= 40 and grade >= 3 and not (tier == "A" and gv == "strong"):
            verdict = "WATCH (40%+ gap, needs Tier A + strong volume)"; why.append("gap ≥40%: historically the worst band")
    if (c.get("regime_qqq") == "red") and grade >= 3:
        why.append("regime red — half size or skip")
    return {"tier": tier, "grade": grade, "verdict": verdict, "why": why}


def card(c: dict, cat: dict, ag: dict) -> str:
    t = c["ticker"]
    g = ag["grade"]
    hl = cat.get("headlines", [])[:4]
    fl = cat.get("filings", [])[:3]
    ev = "\n".join([f"  - SEC {f['form']} {f.get('items','')} — {f['date']} — [filing]({f['url']})" for f in fl] +
                   [f"  - {h['src']} {h.get('date','')} — [{h['title'][:110]}]({h['url']})" for h in hl]) or "  - (nothing found in the last 3 days)"
    tier_txt = {"A": "Tier A?", "B": "Tier B?", "C": "Tier C?", "MA": "M&A target", "unknown": "Unknown"}[ag["tier"]]
    hits = ", ".join(cat.get("pre_tier_hits", [])[:3])
    if cat.get("sec_status") == "error":
        ev += "\n  - ⚠ SEC EDGAR lookup failed this run — filings unknown"
    stop_note = ""
    if c.get("adr_pct") and c.get("price"):
        stop_note = f"ADR {fmt(c['adr_pct'])}% → max stop distance ≈ {fmt(float(c['price'])*float(c['adr_pct'])/100, 2)} (1.0× ADR)"
    return f"""### {t} — {STARS[g]} {g}/5 — {ag['verdict']}
**{c.get('description') or ''}** · {c.get('exchange')} · {c.get('sector') or ''} / {c.get('industry') or ''}
Price {fmt(c.get('price'),2)} · gap **{fmt(c.get('gap_pct'))}%** ({c.get('gap_basis')}) · cap ${fmt(c.get('market_cap_m'),0)}M · float {fmt(c.get('float_m'),1)}M

| Gate | Auto | Numbers |
| --- | --- | --- |
| 0 Regime | {c.get('regime_qqq','?')} | QQQ 10>20 rising = green |
| 1 Catalyst | {tier_txt} | heuristic hits: {hits or '—'} |
| 2 Chart | {c.get('gate_chart_auto','?')} | neglect {fmt(c.get('neglect_score'),0)}/100 · 3m {fmt(c.get('ret_3m_pregap'))}% · 6m {fmt(c.get('ret_6m_pregap'))}% · overhead {fmt(c.get('overhead_pct'))}% · 52w-high {fmt(c.get('dist_52w_high_pct'))}% |
| 3 Volume | {c.get('gate_volume_auto','?')} | {fmt(c.get('kq_vol_ratio'))}× ADV30 ({c.get('kq_vol_ratio_basis')}) · record-day ratio {fmt(c.get('record_vol_ratio'))} (max {fmt(c.get('max_vol_252'),0)} on {c.get('max_vol_252_date')}) |
| 4 Tradable | {c.get('gate_tradability_auto','?')} | $vol proj ${fmt(c.get('dollar_vol_proj_m'))}M · {c.get('tradability_flags') or 'no flags'} |
| Event | {c.get('event_risk') or 'none found'} | next earnings {c.get('next_earnings_date') or '—'}{' (confirmed)' if c.get('next_earnings_confirmed') in (True,'True') else ''} |

**Plan (if it grades ≥3 after you confirm the catalyst):** entry on ORH break (5-min standard) · stop OR-low · {stop_note} · size = (equity × 0.25%) ÷ (entry − stop)
**Why not higher:** {'; '.join(ag['why']) or 'clean on the machine gates — confirm catalyst and read the chart'}
Evidence:
{ev}
"""


def build(date_iso: str, candidates: list[dict], catalysts: dict[str, dict], regime: dict,
          label: str = "v1", top_n: int = 5) -> tuple[str, list[str]]:
    graded = []
    for c in candidates:
        cat = catalysts.get(c["ticker"], {})
        ag = auto_grade(c, cat)
        graded.append((c, cat, ag))
    graded.sort(key=lambda x: (-x[2]["grade"], -(float(x[0].get("kq_vol_ratio") or 0))))
    q, s = regime.get("QQQ", {}), regime.get("SPY", {})
    n_trade = sum(1 for _, _, ag in graded if ag["grade"] >= 4)
    n_three = sum(1 for _, _, ag in graded if ag["grade"] == 3)
    lines = [f"# EP Brief {date_iso} ({label}) — {now_et().strftime('%H:%M')} ET",
             "",
             f"> [!{'success' if regime.get('gate0')=='green' else 'danger'}] Gate 0 regime: **QQQ {q.get('state','?')}** "
             f"(10d {q.get('sma10')} / 20d {q.get('sma20')}, rising: {q.get('sma10_rising')}/{q.get('sma20_rising')}) · "
             f"SPY {s.get('state','?')} · as of {q.get('asof')}",
             f"> {len(graded)} screener hits · {n_trade} grade 4–5 · {n_three} grade 3 · scan mode: {candidates[0].get('scan_mode') if candidates else '—'} · data 15-min delayed",
             "",
             "Machine grades are provisional: catalyst tiers are keyword heuristics until confirmed by reading the PR/filing. "
             "Chart gate = neglect score only; overhead % is recorded, not enforced (hypothesis). Nothing here is a trade until it triggers.",
             "", "## Top candidates", ""]
    for c, cat, ag in graded[:top_n]:
        lines.append(card(c, cat, ag))
    lines += ["## Everything else", "",
              "| Ticker | ★ | Verdict | Tier? | Gap% | ×ADV | Rec | Neglect | Overhead% | $vol M | Event | Flags |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c, cat, ag in graded[top_n:]:
        lines.append(f"| {c['ticker']} | {ag['grade']} | {ag['verdict']} | {ag['tier']} | {fmt(c.get('gap_pct'))} | {fmt(c.get('kq_vol_ratio'))} | "
                     f"{fmt(c.get('record_vol_ratio'))} | {fmt(c.get('neglect_score'),0)} | {fmt(c.get('overhead_pct'),0)} | {fmt(c.get('dollar_vol_proj_m'),0)} | "
                     f"{c.get('event_risk') or ''} | {c.get('tradability_flags') or ''} |")
    watch = [c["symbol"] for c, _, ag in graded if ag["grade"] >= 3 and c.get("symbol")]
    lines += ["", "## Watchlist", "", "`⚡EP Candidates` ← " + (", ".join(watch) or "(none ≥3★)"), "",
              "---", "Rules: rules/rubric-v2.md · Data basis recorded per field in data/candidates.csv · Grades frozen at snapshot time."]
    text = "\n".join(lines)
    prev = BRIEFS / f"{date_iso}.md"
    if label != "v1" and prev.exists() and "(v1)" in prev.read_text()[:120]:
        (BRIEFS / f"{date_iso}-v1.md").write_text(prev.read_text())   # keep the 07:45 brief + its analyst pass
    prev.write_text(text)
    (BRIEFS / f"watchlist-{date_iso}.txt").write_text("\n".join(["NASDAQ:QQQ"] + watch) + "\n")
    # persist grades next to candidates for the outcomes job
    grades_path = BRIEFS / f"{date_iso}.grades.json"
    grades_path.write_text(json.dumps({c["ticker"]: {**ag, "snapshot_et": c.get("snapshot_et"), "label": label}
                                       for c, _, ag in graded}, indent=1))
    return text, watch
