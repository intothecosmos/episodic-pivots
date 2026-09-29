# Log note template

File: `Log/YYYY-MM-DD TICKER.md`. Frontmatter keys are the integration contract — Obsidian Dataview reads them today, the Portfolio Engine parses them later. Never rename keys; add new ones only at the bottom.

```markdown
---
type: ep-eval
ticker: REPL
date: 2026-08-02
grade: 4
verdict: trade        # trade | watch | no-trade
catalyst_tier: A      # A | B | C | unknown
catalyst: "Q2 blowout, rev +48% YoY, guidance raised"
recheck: false
gate_chart: pass      # pass | fail
gate_volume: pass
gate_tradability: pass
gap_pct: 109.2         # canonical: regular-session open vs prior close; pre-open evals may record premkt gap — update at the open
rel_vol_at_time: 4.7   # nullable when no clean at-time multiple; note basis in Evaluation
float_m: 77.6
mkt_cap_m: 941
entry_trigger: 5m-ORH
entry:                # filled at execution
stop:
risk_pct: 0.25
shares:
taken:                # true | false — set on backfill
exit_price:
exit_date:
r_multiple:           # (exit − entry) / (entry − stop)
mistakes: []          # e.g. [chased, early-entry, moved-stop, oversized, ignored-gate]
event_risk:           # e.g. "PDUFA 2026-08-02" or "earnings 2026-08-06" — empty if none
status: evaluated     # evaluated | open | closed | skipped | no-trade | watch-event
                      # mapping: NO-TRADE verdict -> no-trade · TRADE verdict Matt passed on -> skipped
                      # WATCH -> evaluated · event-capped -> watch-event · position live -> open · done -> closed
---

## Evaluation
<verdict card pasted here>

## Notes
<anything Matt said, chart observations, what the tape did>

## Updates
<re-checks, catalyst upgrades, outcome notes — appended, never overwritten>
```

Backfill mode fills: entry, stop (actual), taken, exit_price, exit_date, r_multiple, mistakes, status.
R-multiple: (exit − entry) ÷ (entry − stop). Losses are negative R. Skipped setups get `taken: false`, `status: skipped` — they matter for selectivity stats.
