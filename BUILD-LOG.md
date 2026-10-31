# BUILD LOG — EP data capture v2.1

Spec: `plans/ep-data-capture-v2.1-prd.md` (approved by Matt 2026-10-30, all decisions). This file is the
build's state: a fresh session reads it to know where the last run stopped, what it decided, and what to do
next. Update it in the same commit as the step it describes.

Nightly build task: **"EP v2.1 nightly build"** (`trig_` id in the table below), 21:00 ET every night.
Each run: housekeeping → the first step not DONE → verify against a past date → commit → update this log →
push. Disables itself after step 6 is DONE and emails Matt once. Emails Matt otherwise only when BLOCKED.

## Build rules (from Matt, 2026-10-30)
- One step per night, one commit per step: `auto: v2.1 step N — <title>` (session commits drop `auto:`).
- Verify each step against a past date before enabling anything that runs on a schedule.
- No rubric/gate/sizing change. No CSV key renames; new columns append at the END. No account size or risk
  dollars in the repo. Keyless sources only. Grades frozen.
- Email Matt (Gmail `send_message` to mattdufton@gmail.com) ONLY when step 6 is done or a step is BLOCKED
  (same step failed on two consecutive runs). No other mail, no push from this task.
- Existing scheduled tasks are changed only where the PRD says (steps 3, 5, 6). Prefer `update_trigger`.
  Where a change needs recreation (notification channels cannot be updated in place), create the new task,
  **disable** the old one (never delete), record both ids here.

## Status
| Step | Deliverable | Status | Commit | Verified against |
|---|---|---|---|---|
| 1 | `scripts/intraday.py`; `data/intraday/` archive; `coverage.csv`; backfills 1m/5m/1h | **DONE 2026-10-30** | `v2.1 step 1 — intraday archive + backfills` | CVNA 2026-10-29 (1m: OHLC exact, ORH 67.71/ORL 63.81 = outcomes.csv), CHMI 2026-08-10 (1h), AMZN 2025-10-31 (1h) |
| 2 | `scripts/market.py`; `data/market.csv` backfilled 2025-04-01→; EOD breadth query | **DONE 2026-10-30** | `auto: v2.1 step 2 — market.csv (index trend, VIX, Gate 0, EOD breadth)` | `market.py --verify`: gate0 = `regime_qqq` on all 23 scan days 2026-09-29→10-30 (incl. the 10-15 green→red flip) and QQQ SMA10/SMA20 = the Briefs' Gate 0 line to the cent on all 23; 399 rows 2025-04-01→2026-10-30, no blank index/VIX cells |
| 3 | Evening job: archive `--update`, `market.py --today`, EOD events (`scripts/eod.py`, `data/eod_events.csv`), outcomes rows `source=eod` | NEXT | | |
| 4 | Intraday features → end of `outcomes.csv` (+ `data/historical_features.csv`); `sim_r10_or15/30/60`; `stats.py --by/--or/--source` | pending | | |
| 5 | `data/analyst.csv` + enums (`scripts/analyst.py`); 07:45 machine-only; 09:10 union grading + ISSUE/OPPORTUNITY/quiet message; push/model changes; JSON backfill; CLAUDE.md + README | pending | | |
| 6 | Weekly review restructure (Data health first; regime/breadth/OR tables; Matt items as counts); disable build task; completion email | pending | | |

## Scheduled tasks (ids)
| Task | id | Schedule (ET) | Push | Email | Model |
|---|---|---|---|---|---|
| EP brief v1 (premarket scan) | `trig_01QXzCkN7B1HwFAvREU75buJ` | 07:45 Mon–Fri | on | on | claude-fable-5-1 |
| EP brief v2 (09:10 refresh) | `trig_01CzQuySQV4FBri6ymrEgnU7` | 09:10 Mon–Fri | on | on | claude-fable-5-1 |
| EP outcomes (evening) | `trig_01NnNPMNTRHevESf2eVSFmgf` | 16:35 Mon–Fri | on | off | claude-fable-5-1 |
| EP weekly evidence review | `trig_01WksgVACWi11ddnNnGRq2Hh` | Sun 10:10 | on | on | claude-fable-5-1 |
| EP v2.1 nightly build | `trig_0121YadM14kKeHKxV28MrpYf` | 21:00 daily (first run 2026-10-30) | off | off | claude-fable-5-1 |
Prompt copies live in `scripts/prompts/` (`morning.txt`, `evening.txt`, `build-nightly.txt`); keep them in
sync when a prompt changes. Target state after step 5: push ON only for 09:10; 07:45 + evening on
`claude-sonnet-5-5`; 09:10 + Sunday stay on `claude-fable-5-1`.

## Housekeeping every nightly run (before the step)
1. `python intraday.py --update` — refetches incomplete event files and archives new candidates/EOD events.
   Needed until step 3 wires it into the evening job; harmless afterwards.
2. After step 2 (now active): `python market.py --today` (until step 3 wires it into the evening job).
3. Commit housekeeping data separately as `auto: v2.1 nightly data <date>` before starting the step.

## Step specs — decisions already made, do not re-decide

### Step 1 (done) — how the archive is laid out
- `data/intraday/{TICKER}/{D0}.csv.gz`: sessions D0..D0+5 where D0 = first trading day ≥ event date
  (= `outcomes.trigger_date`). "Sessions 1–5 after the trigger date" in the PRD is read as D0 plus five.
- `data/intraday/{TICKER}/{D0}.pre14.csv.gz`: the 14 sessions before D0, capped at 5m — the baseline for
  `rvol_5m_own14`. Fetched once (it is the past).
- Columns `ts,open,high,low,close,volume,basis`; ts in ET with offset; every row carries its basis.
- Basis by age of D0 at fetch time: ≤29d 1m → ≤59d 5m → else 1h; fallbacks in that order.
- Only completed sessions are stored (complete = after 20:05 ET). A file fetched before D5 has passed is
  `complete=False`; `--update` refetches it from scratch (daily refetch keeps D0 inside the 1m window).
- Old events (>59d) fetch D-14..D5 in one 1h request, split into the two files.
- `coverage.csv` columns: ticker,date,window(event|pre14),source(live|hist|eod),basis,status(fetched|empty|
  error|pending),rows,sessions,sessions_target,first_ts,last_ts,complete,attempts,fetched_at,note.
  Empty/error files are retried at most 3 times.
- 2025 NYSE holidays added to `common.NYSE_HOLIDAYS` (needed for the 2025 historical sessions).

### Step 2 (done) — `market.csv`
- `scripts/market.py --backfill` (2025-04-01 → last complete session) and `--today` (append/replace today).
- Columns, in this order: `date`; for each of QQQ,SPY,IWM,XBI the 13 PRD fields prefixed `qqq_`, `spy_`,
  `iwm_`, `xbi_` (`close,sma10,sma20,sma50,sma10_slope3_pct,sma20_slope3_pct,above10,above20,s10_gt_s20,
  sessions_since_cross,dist_sma10_pct,dist_sma20_pct,dist_52w_high_pct`); `vix_close`; `gate0`,
  `gate0_sessions`; breadth `up4_count,down4_count,up4_ratio_10d,pct_above_sma20,pct_above_sma50,
  new_52w_highs,new_52w_lows,breadth_universe,breadth_basis`; `scan_hits,eod_events`; `ep10_gap_held_pct,
  ep10_d1low_held_pct,ep10_median_ret5d`; `computed_at`.
- `gate0` uses exactly `scan.regime()`'s rule (rubric Gate 0: QQQ SMA10 > SMA20 and both rising vs 3
  sessions ago) → `green|red`; `gate0_sessions` = sessions since the last flip. Import/replicate, don't fork.
- Daily bars: `data_sources.history(sym, years=2)` (stockanalysis 5Y → nasdaq → yfinance). VIX: yfinance
  `^VIX` daily (stockanalysis has no index history) — record `vix_basis`-style note in the docstring if a
  fallback is used. `dist_52w_high_pct` needs 252 prior sessions → bars from 2024-04 (years=2 gives it).
- Breadth: ONE `tradingview_screener` query, US (NYSE/NASDAQ/AMEX), `market_cap_basic >= 100e6`, select
  `change, close, SMA20, SMA50, price_52_week_high, price_52_week_low, high, low`, limit 8000; compute counts
  locally. `up4_ratio_10d` = up4/(up4+down4) summed over the trailing 10 rows (blank until 10 live days).
  Breadth columns stay blank on backfilled rows (`breadth_basis` = `eod_scanner` only on live days).
- `scan_hits` = unique tickers in `candidates.csv` for that date; `eod_events` from `eod_events.csv` (step 3,
  blank until then). `ep10_*` from `outcomes.csv` rows with `trigger_date` in the trailing 10 scan days.
- Verify against a past date: `market.csv` `gate0` on 2026-10-23 and 2026-10-29 must equal the
  `regime_qqq` recorded on those dates' `candidates.csv` rows, and the QQQ sma10/sma20 must match
  `Briefs/<date>.md` Gate 0 line (within rounding). Print the comparison in the run log.
- Do NOT wire into the evening job yet (step 3). The nightly build runs `--today` meanwhile.
- As built (2026-10-30): `scan.gate0_rule(closes)` was factored out of `scan.regime()` (output verified byte-identical)
  and `market.py` imports it — one definition of Gate 0. `sessions_since_cross`/`gate0_sessions` count
  consecutive sessions in the current state including the day itself (1 = flip day). Breadth universe =
  `scan._base_conds()` (US common stock, cap ≥ $100M; ~3,900 names). `vix_close` = yfinance `^VIX`, with
  CBOE `VIX_History.csv` (keyless, official, next-morning) filling any date yfinance lacks. `--today` also
  refreshes the two previous rows' non-breadth columns. Verification compares the brief dated D with the
  market.csv row the brief names ("as of <date>", normally D−1, because the morning run judges the last
  completed session). `--verify` is a CLI mode so later runs can re-check.

### Step 3 — evening job
- `scripts/eod.py --date D` (default: today): scanner query with the historical definition — `gap >= 8`
  (open vs prior close), `volume >= 3 × average_volume_30d_calc`, `close >= 0.5`, `market_cap_basic >= 100e6`,
  US common stock. Write `data/eod_events.csv`: `symbol,ticker,exchange,date,snapshot_et,in_morning_scan,
  <same machine fields as candidates.csv where the scanner provides them>,eod_basis`. One row per ticker-day,
  frozen (never overwritten). `in_morning_scan` = ticker-day present in `candidates.csv`.
- `outcomes.py`: add targets from `eod_events.csv`; append column `source` (`live|eod`) at the END of
  `OUTCOME_COLUMNS` (`live` for existing rows). Keyed (ticker,date) — a ticker-day in both stays `live`.
- Evening job prompt (`scripts/prompts/evening.txt` + `update_trigger` on the evening task): after
  outcomes.py run `python eod.py && python intraday.py --update && python market.py --today`; commit
  `auto: outcomes <date>` as before. Final message adds one line: `Capture: <n> EOD events (<k> new vs
  morning) · bars <fetched>/<expected> · market.csv <date> ok/FAILED`.
- Decision (flagged to Matt 2026-10-30, default stands unless he objects): move the evening task to
  **20:35 ET** so D0's post-market bars (to 20:00) are complete when archived and `market.csv` uses final
  closes. Push is off for this run after step 5 anyway. Use `update_trigger` cron
  `CRON_TZ=America/Toronto 35 20 * * 1-5`. Update README's schedule table and CLAUDE.md "Where things run".
- Verify against a past date: `python eod.py --date 2026-10-29 --dry-run` evaluated on `outcomes.csv`
  daily fields must select CVNA (gap_open 10.55%, d1_vol 23.2M ≫ 3× ADV30) and must NOT select CMG
  (gap_open 6.02%), and flag `in_morning_scan` correctly (both were morning candidates); `intraday.py --update` on a dry past date is idempotent (0 refetches of
  complete files). Note: the scanner is a snapshot — a past-date query returns today's values, so the dry run
  verifies the query shape and the join, and the first live run verifies counts.

### Step 4 — features
- `scripts/features.py`: pure functions `event_features(bars_event, bars_pre14, daily_row, candidate_row)
  -> dict` producing exactly the PRD §2 fields plus `vol_scale` (consolidated d1 volume ÷ regular-hours bar
  volume sum; see Findings — Yahoo intraday volume) and `bars_basis`. `pm_vol` comes from
  `candidates.premarket_volume` (09:10 row preferred), never from bars (extended-hours bar volume is 0).
  `pm_high/pm_low` from bars 04:00–09:29. Volume features are reported raw from bars; `*_x_adv30` use
  `vol_scale`-adjusted sums; `rvol_5m_own14` is within-feed (no scaling). For 1h-only files populate only
  `vol_60m, vol_60m_x_adv30 (scaled), orh_60, orl_60, hod_min/lod_min at 60-min resolution, vwap_d1,
  close_vs_vwap_pct, close_in_range_d1, gap_filled_d1, float_turnover_d1, bars_basis`.
- `outcomes.py`: append the PRD §2 columns (then `sim_r10_or15, sim_r10_or30, sim_r10_or60`, then
  `vol_scale`) at the END of `OUTCOME_COLUMNS`; existing values unchanged; `or_basis/orh/orl` keep meaning
  the 5-min OR (rubric v2). Fill from the archive when a file exists; else leave blank (never refetch bars
  here — the archive is the source).
- Historical events: `data/historical_features.csv` keyed (ticker,date) with the same feature columns
  (separate file because `historical.py --events` regenerates `historical_eps.csv`).
- `stats.py`: `--source live|eod|hist|all` (default hist = current behaviour), `--by regime|breadth`
  (join `market.csv` on trigger_date: regime = gate0; breadth = up4_ratio_10d terciles, live rows only),
  `--or 5|15|30|60` (which `sim_r10*` column the R stats use). W40–W43 reviews must reproduce with defaults.
- Verify against a past date: CVNA 2026-10-29 → `orh/orl` unchanged (67.71/63.81), `orh_15/orl_15` etc.
  computed and printed; `vol_scale` ≈ 0.69 (23.23M/33.61M); AMZN 2025-10-31 (1h) → 60-min fields only.

### Step 5 — analyst.csv, prompts, notifications, models, CLAUDE.md
- `scripts/analyst.py`: `validate <json>` (enums), `normalize` (map legacy labels: `A?`→A, `B?`→B, `C?`→C,
  `n/a`/`unknown`/`Unknown`→Unknown, `MA`/`M&A`/`MA-target`→MA-target; verdict `TRADE (small)`→TRADE-small
  etc.), `backfill` (every `Briefs/*.analyst.json` → `data/analyst.csv`, `graded_at` = the brief's analyst
  pass timestamp; these are the original frozen grades, not hindsight), `append <date>` (today's union).
  `data/analyst.csv` columns exactly as PRD §5. One row per ticker-day; never overwritten.
- 07:45 prompt: machine-only (steps 1–4 + commit + watchlist best-effort; no analyst pass, no JSON).
  Final message: `EP scan v1 <date> — regime <g/r> — <n> hits (machine) · Brief: Briefs/<date>.md`.
- 09:10 prompt: grade the UNION of 07:45 and 09:10 hits once (rubric v2 Gate 1 research as today), write
  `Briefs/<date>.analyst.json` AND `python analyst.py append <date>` (validate before commit; invalid
  enum → fix the JSON, never commit an invalid row). Check yesterday's evening commit exists and
  `intraday.py --report` coverage ≥95% for live events of the last 5 sessions. Final message order:
  `ISSUE:` lines → `OPPORTUNITY:` lines (★4+ TRADE, or ★3+ Tier A with strong volume in green regime) →
  else one line `EP quiet — n hits, nothing ≥4★`; then watchlist lines and Brief path. Under 12 lines.
- Notifications/models: `update_trigger` the 09:10 task prompt (push stays on). For 07:45, evening and
  Sunday the push channel must go OFF with email ON — `update_trigger` cannot change channels, so
  `create_trigger` a replacement with the same cron/prompt and `notifications: {push:false,email:true}`,
  then `update_trigger` the OLD one `enabled:false` (keep it, don't delete), then `update_trigger` the NEW
  07:45 and evening tasks `model: claude-sonnet-5-5` (PRD §8; Matt approved). Record all ids above.
- CLAUDE.md: "Where things run" → 07:45 machine scan, 09:10 analyst grade (union, push), evening 20:35
  outcomes+capture, Sunday review, 21:00 build (until done); add `data/intraday/`, `market.csv`,
  `eod_events.csv`, `analyst.csv`, `historical_features.csv`, `plans/`, `BUILD-LOG.md` to Layout; drop the
  10:15 snapshot. README schedule table and script table likewise. `scripts/prompts/*.txt` updated.
- Verify against a past date: `analyst.py backfill` row count = number of graded tickers across all
  `Briefs/*.analyst.json`; every row passes `validate`; spot-check 2026-10-29 rows against the brief text.
  Dry-run the new 09:10 message logic on 2026-10-29's data (expect `OPPORTUNITY:` or `quiet`, no `ISSUE`).

### Step 6 — weekly review
- Sunday prompt: section order `## Data health` (runs this week: 07:45/09:10/evening commits present per
  weekday; candidates rows; EOD events; bar coverage % from `intraday.py --report`; `market.csv` last date;
  repo size; source failures from coverage notes) → `## This week` → `## Rules on trial` (+ regime-split,
  breadth-split, OR-length tables from `stats.py --by regime`, `--by breadth`, `--or 15/30/60`, each with
  n) → `## Proposed rubric changes` → `## Housekeeping` (Log notes needing Matt as COUNTS only, last).
  Email first five lines must answer "is anything broken?". `stats.py --health` may be added to produce the
  Data health block mechanically (preferred).
- Verify against a past date: regenerate 2026-W43 with the new structure into the scratch dir and confirm
  the `Rules on trial` numbers equal `Reviews/2026-W43.md` (defaults unchanged).
- Then: completion email to Matt (what was built, step by step; decisions flagged; findings; coverage
  numbers; what to watch in the first week), `update_trigger` the build task `enabled:false`, final commit
  `auto: v2.1 step 6 — weekly review restructure; build complete`.

## Decisions made during the build (flag to Matt in the completion email)
- 2026-10-30 (session): D0 = the trigger day itself is archived (PRD said "sessions 1–5 after"); the file
  holds D0..D5. Lookback window `pre14` added (14 prior sessions, 5m cap) because `rvol_5m_own14` needs it.
- 2026-10-30 (session): extended-hours volume in Yahoo bars is zero → `pm_vol` stays on the scanner's
  `premarket_volume`; intraday volume features get a `vol_scale` so ADV ratios are consolidated-volume
  consistent. See Findings.
- 2026-10-30 (session, for step 3): evening task moves 16:35 → 20:35 ET. Default unless Matt objects.
- 2026-10-30 (session, for step 5): old tasks whose notification channels change are disabled, not deleted.
- 2026-10-30 (nightly, step 2): stockanalysis's 5Y history endpoint can serve the current session from a
  stale intraday cache (QQQ 2026-10-30 close 687.15 / vol 58M vs 690.49 / 85M on the 1Y endpoint minutes
  later, and `history()` caches the 5Y result 6h). `market.py` therefore always merges the uncached 1Y
  range and keeps, per date, the row with the larger volume. `scan.regime()` (1Y) was never affected.
- 2026-10-30 (nightly, step 2): `ep10_d1low_held_pct` counts only rows with ≥ 2 sessions known (D1-only
  rows hold their low trivially); `ep10_gap_held_pct` = D1 close > prior close. Health gauges, not grades.

## Findings
- Yahoo/yfinance intraday (verified 2026-10-30 on CVNA, CMG, NRXP, CPRI, AMZN, META): extended-hours bars
  carry prices but ZERO volume; one post-close bar (16:00–16:02) often carries a large late volume print;
  regular-hours bar volume ÷ consolidated daily volume ranged 0.47×–1.72× (CVNA 1.45, CMG 0.88, NRXP 0.47,
  CPRI 1.72, AMZN 0.68, META 0.93, CHMI 0.99). OHLC reconciles exactly. Consequence: volume ratios must be
  within-feed (own-window RVOL) or scaled by the daily bar; never compare raw bar volume to ADV30.
- 1m requests accept an 8-calendar-day span (PRD said 7); `intraday.py` uses 7 to be safe.
- Throughput ~100 events/min for 1h history (one request per event, 0.25s sleep, no rate-limit hits);
  ~45 events/min for 1m+5m live events.
- Historical symbol mismatches (ticker changes/relistings since the event): 126 of 2,476 `historical_eps.csv`
  rows (5.1%) return empty at 1h — Yahoo stitches daily history across a symbol change but not intraday.
  Logged as `status=empty` in coverage.csv, excluded from intraday stats, kept in the daily-bar baseline.
  Live lookbacks empty for BMMX 2026-10-15 (IPO that day) and NANO 2026-10-22 (symbol reassigned that day).
- yfinance 1.7: per-symbol error text lives in `yfinance.shared._ERRORS` (must be imported as a module).
- Breadth at 2026-10-30 EOD (QQQ −3.5% day, first live row): universe 3,889; up4 109 / down4 835;
  56.5% above SMA20, 45.9% above SMA50; new 52w highs 193 / lows 158. `up4_ratio_10d` fills from the 10th
  live row (≈2026-11-12). One scanner query, ~1.5 s, no rate-limit.
- Gate 0 history 2025-04-01→2026-10-30: 200 green / 199 red sessions, 25 flips; longest green runs
  2025-04-29→08-01 and 2026-04-13→06-08; the current red run started 2026-10-15 (12 sessions).
- yfinance crumb fetch returned HTTP 429 once at 21:06 ET; the `^VIX` download still succeeded. The CBOE
  CSV covers every session but today, so a yfinance outage blanks only the current day's `vix_close` until
  the next night's refresh of the previous rows.

## Run log (newest first)
- 2026-10-30 21:00–21:12 ET, nightly run 1 (step 2). Housekeeping: `intraday.py --update` touched 42
  events (refetched the incomplete 1m files for 10-23→10-29, archived CPRI/NRXP 2026-10-30); live event files
  138/138 fetched (99 complete), hist 2350/2476 (unchanged, 126 symbol-change empties); archive 13.9 MB /
  4,966 files; committed `auto: v2.1 nightly data 2026-10-30`. Step 2: wrote `scripts/market.py`
  (--backfill/--today/--verify) and `data/market.csv` (399 rows 2025-04-01→2026-10-30, 144 KB; backfill
  2.7 s from cached bars). Verification `market.py --verify`: 23/23 scan days gate0 = candidates
  `regime_qqq` (green through 10-15's brief, red from 10-16's), 23/23 QQQ SMA10/SMA20 equal to the brief
  line to the cent (e.g. brief 2026-10-23: 727.33/737.24 = market.csv 2026-10-22; brief 2026-10-29:
  716.69/732.48 = market.csv 2026-10-28). Re-running --backfill then --today → 0 cell changes (idempotent;
  live breadth preserved). First live breadth row written for 2026-10-30 (see Findings). Side change:
  `scan.gate0_rule()` factored out of `scan.regime()` (regime() output identical before/after). README
  gained the market.py lines. Odd: `add_repo` tool was not present in this session (repo was already
  cloned and in scope, so no effect). Next: step 3 (evening job: eod.py, outcomes `source`, task move to
  20:35).
- 2026-10-30 19:10–20:05 ET, interactive session with Matt (approval + step 1). Live backfill 138 events in
  3.2 min (121×1m, 15×5m, 2 pending = today's D0 not complete before 20:05); historical 1h backfill 2,476
  events in 23 min. Final coverage: event files hist 2350/2476 fetched (94.9%, 2345 complete), live 136/138;
  pre14 hist 2342/2476, live 136/138. Empties = 126 hist events whose symbol has since changed/relisted
  (Yahoo keeps no intraday history under the old symbol; daily history exists, e.g. NAKA, RTB, WBD, SLP) and
  a few listing-day events (first bar after D0: RDNW, ABTC). Archive 13.7 MB gz in 4,964 files. `--verify` OK
  on CVNA 2026-10-29 (1m), ULCC 2026-10-28 (1m), CHMI 2026-08-10, AMZN 2025-10-31, META 2025-07-31, VNDA
  2026-02-23, LEVI 2026-04-08 (1h). Re-running `--backfill` → 0 events (idempotent); retries capped
  (empty/error 3, stale-incomplete 2). Created the nightly build task (`trig_0121YadM14kKeHKxV28MrpYf`,
  first run tonight 21:00) and this log. Next: step 2.
