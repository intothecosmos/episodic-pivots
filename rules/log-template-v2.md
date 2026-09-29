# Log note template v2

File: `Log/YYYY-MM-DD TICKER.md`. Frontmatter keys are the integration contract (Obsidian
Dataview + Portfolio Engine). **Never rename a key; new keys append at the bottom.** The body is
for humans: header callout first, evidence table, plan, notes, updates, and an auto-appended
outcome block the nightly job maintains.

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
gap_pct: 109.2
rel_vol_at_time: 4.7
float_m: 77.6
mkt_cap_m: 941
entry_trigger: 5m-ORH
entry:
stop:
risk_pct: 0.25
shares:
taken:
exit_price:
exit_date:
r_multiple:
mistakes: []
event_risk:
status: evaluated     # evaluated | open | closed | skipped | no-trade | watch-event
# ---- v2 keys (append-only) ----
graded_at: 2026-08-02 08:05      # when the grade was frozen; hindsight: true if written after the outcome was knowable
hindsight: false
regime: green                    # Gate 0 at evaluation time
auto_grade: 4                    # machine grade from the brief, if any
kq_vol_ratio: 4.7                # volume ÷ 30d ADV at evaluation (basis in body)
record_vol_ratio: 1.3            # volume ÷ largest day in prior 252 sessions
neglect_score: 82
overhead_pct: 12
adr_pct: 6.1
ret_5d:                          # filled by outcomes.py
ret_20d:
sim_r10:
d1_low_held:
---
<!-- header:auto -->
> [!success] REPL — ★★★★☆ 4/5 — TRADE
> Tier A · gap 109.2% · rel vol 4.7× · cap $941M · float 77.6M · Chart pass · Volume pass · Tradability pass
> Q2 blowout, rev +48% YoY, guidance raised
<!-- /header:auto -->

## Evaluation

| Gate | Result | Evidence |
| --- | --- | --- |
| 0 Regime | green | QQQ 10>20, both rising |
| 1 Catalyst | Tier A | [PR title](link) — one line on why this tier |
| 2 Chart | pass | 9 months sideways, gapping to 2-yr high; neglect 82, overhead 12% |
| 3 Volume | pass | 4.7× ADV by 9:45; projects to 1.3× the largest day in a year |
| 4 Tradable | pass | $11.20, $941M cap, 4.6M premkt vol, spread ≈ 3% of stop |
| Event | none | next earnings Nov 5 (outside window) |

**Plan:** entry 5-min ORH break · stop OR low · max stop 1.0× ADR (0.68) · size = (equity × 0.25%) ÷ (entry − stop)
**Weakness:** one line.

## Notes
What Matt said, chart observations, what the tape did.

## Updates
- YYYY-MM-DD: re-checks, catalyst upgrades, fills, exits — appended, never overwritten.

<!-- outcome:auto -->
(maintained by scripts/outcomes.py — do not edit by hand)
<!-- /outcome:auto -->
```

Callout type by verdict: `success` = TRADE, `warning` = WATCH, `failure` = NO TRADE.
Backfill mode fills: entry, stop, taken, exit_price, exit_date, r_multiple, mistakes, status.
R-multiple = (exit − entry) ÷ (entry − stop). Skipped setups: `taken: false`, `status: skipped`.
