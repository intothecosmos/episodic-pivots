# EP data capture v2.1 — PRD ("no Matt in the loop")

Status: **APPROVED 2026-10-30** — all decisions approved by Matt ("proceed with v2.1 as written"). Build in
progress, one step per night; progress and step-level decisions live in `BUILD-LOG.md`. This file is the
repo copy of the Claude Project doc `claude/ep-data-capture-v2-1-prd.md` (v0.2, 2026-10-27).
Extends EP Workflow v2. Rubric v2 untouched. Grades stay frozen.

## Problem

The pipeline was built as decision support with Matt closing the loop (Log notes, `decisions.csv`). Four weeks in, the loop is empty and will stay mostly empty. That is fine for machine data, but the pipeline under-captures exactly the data that doesn't need him:

- **Intraday:** only the first 5-min bar's high/low and two booleans survive each candidate's day. The 5-min bars are fetched nightly and discarded. `outcomes.py` already has a "window aged out" fallback — data loss by design.
- **Regime:** `scan.regime()` computes QQQ/SPY close, SMA10/20 and rising flags, but only a green/red bit reaches `candidates.csv`, and only on rows with a candidate. The 2,476-event historical baseline cannot be regime-split because no regime series exists.
- **Analyst output:** catalyst tier (the one feature history can't provide) lives in per-day JSON with free-text labels (`A?`, `n/a`, `MA`, `M&A`, `MA-target`, `unknown`/`Unknown`).
- **Event definition mismatch:** live = premarket gap ≥8% at 07:45/09:10; historical = open gap ≥8% AND day volume ≥3× ADV30. The two sets cannot be pooled, and live misses EPs that develop after the open.
- **10:15 snapshot** in CLAUDE.md was never built; Gate 3 is scored on a premarket ratio that under-reads (92/144 "fail").

## Principle

Persist what expires; derive what doesn't. Raw bars are the insurance policy. Small, basis-tagged derived set. No data path depends on a human. Unify definitions so datasets pool.

## Verified facts (2026-10-27, from the cloud container)

- yfinance: 1m bars available ≤30 days back (7-day span per request, pre/post works, small caps OK); 5m ≤60 days; 1h ≤730 days, bars aligned 09:30/10:30/…/15:30. Symbol mismatches return empty silently (SAIQ) → coverage must be logged.
- Zarattini, Barbon & Aziz (2024), 7,000+ US stocks 2016–2023: ORB edge concentrates in "stocks in play" = top RVOL where RVOL = first-5-min volume ÷ 14-day average of that window; 5/15/30/60-min ranges all tested; stop = 0.1× 14-day ATR; exit at close. Day-trading evidence, supportive not conclusive for swing EPs. Sources: concretumgroup.com (paper page), cxoadvisory.com (methodology summary).

## What is recorded today vs. should

| Layer | Today | Should |
|---|---|---|
| Premarket snapshot | 57 fields at 07:45 and 09:10, frozen | unchanged |
| Intraday bars | fetched 5-min, discarded | 1-min pre/post, sessions 1–5, gz, archived; backfills (below) |
| Opening range | first 5-min bar only | 5/15/30/60-min definitions, break/stop timing, reclaim |
| Volume confirmation | premarket ratio only | first 5/15/30/60-min vs ADV30 **and vs own 14-day same-window average** |
| Regime | green/red bit per candidate row | daily `market.csv` + breadth, backfilled to 2025-04-01 |
| Event universe | premarket gappers only | + EOD events with the historical definition, flagged |
| Catalyst | free-text tier in JSON | `analyst.csv`, enforced enums, one grade per ticker-day |
| Human decisions | empty | no dependency; Log/decisions stay available |
| Options / SI / borrow | none | out of scope (no reliable keyless source) |

## Changes

### 1. Raw intraday archive
`data/intraday/{TICKER}/{YYYY-MM-DD}.csv.gz` — 1-min OHLCV, `prepost=True`, sessions 1–5 after the trigger date, fetched by the evening job (idempotent; skip existing). Fallback 5m; `bars_basis` recorded. `data/intraday/coverage.csv`: one row per expected file — fetched / empty / error, so coverage % is reportable.
**Backfills (rolling windows — run first):** 1m for all candidates ≤30 days old; 5m for candidates 31–60 days old; 1h for every row in `historical_eps.csv` (2025-04 →) and every live candidate.

### 2. Intraday features → new columns at the END of `outcomes.csv`
`pm_high, pm_low, pm_vol, open_vs_pm_high_pct` · `vol_5m, vol_15m, vol_30m, vol_60m` · `vol_15m_x_adv30, vol_30m_x_adv30` · `rvol_5m_own14` (first-5-min volume ÷ mean first-5-min volume, prior 14 sessions — Zarattini definition) · `orh_15, orl_15, orh_30, orl_30, orh_60, orl_60` · `or_break_min` (minutes after 09:30 the 5-min ORH first broke) · `or_stop_min` · `or_reclaim` · `hod_min, lod_min` · `vwap_d1, close_vs_vwap_pct` · `close_in_range_d1` · `gap_filled_d1` · `d1_close_vs_orh` · `max_r_d1` · `post_trigger_max_dd_pct` · `float_turnover_d1` · `d2_or_break` · `bars_basis`.
Existing columns unchanged. `sim_*` stay on the 5-min ORH (rubric v2). Add `sim_r10_or15`, `sim_r10_or30`, `sim_r10_or60` for comparison. For 1h-only backfill rows, only the 60-min features are populated.

### 3. Daily market table — `data/market.csv`
One row per trading day, written by the evening job, backfilled to 2025-04-01.
Per QQQ, SPY, IWM, XBI: `close, sma10, sma20, sma50, sma10_slope3_pct, sma20_slope3_pct, above10, above20, s10_gt_s20, sessions_since_cross, dist_sma10_pct, dist_sma20_pct, dist_52w_high_pct` · `vix_close` · `gate0` (rubric definition) + `gate0_sessions` (since last flip) · breadth from one TradingView scanner query at EOD (US, cap ≥$100M): `up4_count, down4_count, up4_ratio_10d, pct_above_sma20, pct_above_sma50, new_52w_highs, new_52w_lows` · `scan_hits, eod_events` · EP-internal health (trailing 10 scan days, filled as outcomes mature): `ep10_gap_held_pct, ep10_d1low_held_pct, ep10_median_ret5d`.
Breadth backfill is not available keylessly; index/VIX columns backfill fully.

### 4. EOD event capture — `data/eod_events.csv`
Evening job runs a scanner query with the historical definition (open gap ≥8% vs prior close AND day volume ≥3× ADV30, price ≥$0.50, cap ≥$100M) and writes one row per event with `in_morning_scan` (true/false) and the same machine fields as `candidates.csv` where available. Each EOD event also gets the 1-min archive and an `outcomes.csv` row (`source=eod`). This makes live and historical poolable and captures EPs that developed after the open. Morning candidates that fail the EOD definition stay in `candidates.csv` (they are the negative examples).

### 5. Analyst grading — once, at 09:10
07:45 run becomes machine-only (scan, freeze rows, write the table — no research). 09:10 run grades the **union** of 07:45 and 09:10 hits once; one timestamped, frozen grade per ticker-day. `data/analyst.csv`: `ticker, date, tier, catalyst_type, grade, verdict, event_in_window, why, graded_at`.
Enums enforced in the prompt and validated before commit: `tier ∈ {A, B, C, Unknown, MA-target}`; `catalyst_type ∈ {earnings, guidance, regulatory, contract, partnership, ma-acquirer, ma-target, financing, listing, sympathy, other, none}`; `verdict ∈ {TRADE, TRADE-small, WATCH, NO-TRADE}` (nuance goes in `why`). Existing JSONs backfilled via a normalization map; JSONs keep being written (watchlist.py reads them).

### 6. Notifications and the 09:10 message
Push ON only for the 09:10 run. Its final message leads with whatever needs attention, in this order: (1) `ISSUE:` a failed/missing run or coverage gap (the 09:10 run checks yesterday's evening commit and bar coverage); (2) `OPPORTUNITY:` any ★4+ TRADE, or ★3+ Tier A with strong volume in a green regime; else (3) one line `EP quiet — n hits, nothing ≥4★`. Push OFF for 07:45, evening, Sunday (email stays for all). Push cannot be suppressed conditionally, so "EP quiet" is the ignore signal.

### 7. Weekly review changes
Lead with **Data health** (runs, rows, bar coverage %, market.csv rows, EOD events, repo size, source failures). Add regime-split, breadth-split and OR-length tables. Move "Log notes needing Matt" to the end as counts.

### 8. Model assignment
- 07:45 scan and evening job (mechanical: run Python, commit): Sonnet 5.5. Phase 2: move both to GitHub Actions cron (no model, deterministic, free) once capture code is stable and TradingView-scanner/Yahoo reachability from GH runners is tested.
- 09:10 grade (judgment; errors are frozen forever): keep Fable 5.1.
- Sunday review (numeric reasoning + narrative, weekly): keep Fable 5.1.

### 9. Explicitly not building
10:15 snapshot (superseded by bars; remove from CLAUDE.md). Dashboards. Rubric/gate/sizing changes. Options/SI data.

## Success criteria
1. Every live candidate and EOD event from go-live has 1-min files for sessions 1–5; coverage ≥95% reported weekly; backfills (1m ≤30d, 5m ≤60d, 1h all history) complete and basis-tagged.
2. `market.csv` complete 2025-04-01 → today, appended daily.
3. `stats.py --by regime|breadth`, `--or 5|15|30|60`, `--source live|eod|hist` run end to end.
4. 09:10 push leads with issue/opportunity or says "quiet"; Sunday email's first five lines answer "is anything broken?".
5. No scheduled run depends on a human; the review stops flagging Matt's absence.

## Constraints
No key renames; new columns append at end. No account size/risk dollars in repo. Cloud container only. Keyless sources. Grades frozen. W40–W42 reviews must still reproduce after `stats.py` edits.

## What could break
yfinance is unofficial (mitigation: raw archive makes the past safe; TradingView MCP `get-ohlcv` as second intraday source in agent sessions). Thin names → sparse 1m (fallback 5m, tagged). Symbol mismatches → logged, not silent. Evening runtime +2–4 min. Repo growth ~15–25 MB/month gz incl. EOD events (reassess at 300 MB). Enum pressure on borderline catalysts (`other` allowed, `why` keeps nuance). Historical set still has survivorship bias (today's listings); live/EOD sets do not.

## When there is enough to work with (estimates; winsorized R SD ≈ 1.1, so ~250 trades/group detects a 0.3R difference)
- **~Nov 10, 2026 (after steps 1–3):** regime- and breadth-split of the 2,476-event baseline; 60-min OR + first-hour RVOL on ~2,400 historical events (1h backfill); 5-min OR on ~250–300 events from the last 60 days; 1-min detail on ~100 from the last 30. First real intraday reads, with the historical caveats.
- **~Mar 2027:** live point-in-time n≈250–400 triggered sims (higher with EOD events) → population-level entry mechanics (OR length, first-5/15-min RVOL thresholds, volume confirmation) at ~0.3R resolution.
- **H2 2027:** sub-bucket tests (Tier A × strong volume × green regime) at n≈100–250.

## Plan (one commit each; verified against a past date before enabling)
1. Backfills first (rolling windows): 1m ≤30d, 5m ≤60d, 1h all history + coverage log.
2. `market.csv` + index/VIX backfill + EOD breadth query.
3. Archive step in the evening job + EOD event capture.
4. Intraday features in `outcomes.csv`; `stats.py` splits.
5. `analyst.csv` + enum enforcement; 07:45 machine-only; 09:10 union grading; notification/message changes; model assignment; CLAUDE.md update.
6. Weekly review restructure.
Phase 2 (later): GitHub Actions for the mechanical runs.

## Decisions
- Sessions 1–5 of 1-min bars: **approved 2026-10-30** (implemented as D0 plus the next 5 sessions — see BUILD-LOG).
- Regime refs QQQ/SPY/IWM/XBI + breadth: **agreed 2026-10-27.**
- Grade once at 09:10, 07:45 machine-only: **agreed 2026-10-27.**
- Push only on 09:10, lead with issue/opportunity: **agreed 2026-10-27.**
- EOD event capture, backfill plan, GH Actions phase 2, model assignment: **approved 2026-10-30.**
