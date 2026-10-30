# Episodic Pivots — project brief (CLAUDE.md)

Owner: Matt Dufton. Purpose: a rules-based, data-evolving workflow for trading Episodic Pivots
(Kullamägi-style catalyst gap-ups). This repo is the canonical store for code, data, briefs and
evaluation notes. Matt's Obsidian folder is a clone of it.

Read this file first in every session. The full PRD lives in the Claude Project "Episodic Pivots"
(doc: EP Workflow v2 — PRD). Rules below are the operative summary.

**Build in progress (from 2026-10-30): EP data capture v2.1** — spec `plans/ep-data-capture-v2.1-prd.md`,
state and step-level decisions `BUILD-LOG.md`. A nightly 21:00 ET task completes one step per night and
disables itself after step 6. Read BUILD-LOG.md before touching scripts/, data/ or the scheduled tasks.

## Non-negotiables

- No rubric change ships without Matt's explicit sign-off. Runs may *propose* changes with n attached.
- Grades are frozen at evaluation time. Backfilled grades carry `hindsight: true` and are excluded
  from rubric statistics. Outcomes may be backfilled; grades never.
- Log-note frontmatter keys are an integration contract (Obsidian Dataview + Portfolio Engine parse
  them). Never rename a key. New keys append at the bottom only.
- Account size and risk dollars never enter this repo. Sizing formulas only.
- Never soften a gate to make a trade happen. Most candidates should fail.
- This is process support, not financial advice. The decision to trade is Matt's.

## Layout

```
CLAUDE.md            this brief
README.md            how to run things
BUILD-LOG.md         v2.1 build state: step status, decisions, scheduled-task ids, run log
plans/               PRD copies (ep-data-capture-v2.1-prd.md)
rules/rubric-v2.md   the operative rulebook since 2026-09-30 (gates, entry, stop, sizing, exit)
scripts/             scan.py gates.py catalyst.py brief.py outcomes.py intraday.py (Python 3, keyless sources)
scripts/prompts/     copies of the scheduled-task prompts (keep in sync with the tasks)
data/candidates.csv  one row per ticker-day screener hit, machine gates frozen at snapshot time
data/outcomes.csv    forward returns + simulated trade per candidate row (nightly)
data/decisions.csv   Matt's verdicts/fills, timestamped
data/historical_eps.csv   2,476 historical EP-days 2025-04→2026-08 (daily-bar baseline)
data/intraday/       raw bar archive: {TICKER}/{D0}.csv.gz (D0..D5) + {D0}.pre14.csv.gz (14 prior sessions),
                     basis-tagged (1m/5m/1h); coverage.csv = one row per expected file
data/market.csv      daily regime/breadth table (v2.1 step 2) · eod_events.csv (step 3) · analyst.csv (step 5)
Briefs/YYYY-MM-DD.md morning briefs (v1 07:45, v2 09:10 ET)
Reviews/YYYY-WW.md   weekly evidence reports
Log/YYYY-MM-DD TICKER.md   human-decided evaluations (frontmatter contract in rules/log-template.md)
EP Stats.md          Obsidian Dataview summary (unchanged contract)
pine/                EP Engine indicator + EP Strategy (Pine v6)
```

## Data sources (all tested from the cloud container, no keys)

- TradingView scanner: `tradingview-screener` package → scanner.tradingview.com (15-min delayed, snapshot).
  The official TradingView MCP connector (account: watchlists, price alerts, news, OHLCV, earnings)
  is available in Claude sessions; its screener calls rate-limit — use the direct scanner for scans.
- Daily bars: stockanalysis.com `/api/symbol/s/{sym}/history?range=1Y&period=Daily`
  (needs a full Chrome User-Agent). Fallbacks: api.nasdaq.com historical, yfinance.
- Intraday 1/5-min/1h bars: yfinance → archived in `data/intraday/` by `scripts/intraday.py` (1m ≤30d,
  5m ≤60d, 1h ≤730d). Yahoo quirks: extended-hours bars have prices but zero volume (premarket volume
  comes from the scanner snapshot), and regular-hours bar volume does not reconcile with consolidated
  daily volume (0.5–1.7×) — volume ratios are within-feed or scaled by the daily bar. OHLC is exact.
- Catalysts: SEC EDGAR full-text + 8-K Atom (User-Agent header required), api.nasdaq.com news by
  symbol, GlobeNewswire (curl default UA only), PRNewswire search, finviz quote news, Google News RSS.
- Events: stockanalysis `/api/symbol/s/{sym}/earnings` (has `confirmed`), Nasdaq earnings calendar,
  EDGAR "PDUFA" full-text, marketbeat lock-up table.
- Blocked from cloud: Accesswire, businesswire.com, biopharmcatalyst/rttnews (JS), stooq, raw Yahoo.

## Where things run

- Cloud scheduled tasks (Mac may be asleep): 07:45 scan+brief v1, 09:10 brief v2, 16:35 outcomes
  (moves to 20:35 with v2.1 step 3 so post-market bars are complete), Sunday 10:10 review, and the
  21:00 v2.1 nightly build until it finishes. They write to this repo and send push/email. The 10:15
  post-open snapshot was never built and is superseded by the intraday archive.
- Mac-linked run (when awake): mirrors brief/log into the Obsidian folder, maintains the
  TradingView watchlist "⚡EP Candidates" via the MCP connector.
- Real-time triggers: Matt's TradingView + the Pine "EP Engine" indicator alert on the watchlist.
  The cloud is never the execution feed.

## Conventions

- Times in ET. Dates ISO. Tickers as EXCHANGE:TICKER in data files, bare ticker in note filenames.
- Every machine field records its basis (e.g. `kq_vol_ratio_basis: premarket|first15|fullday`).
- Weekly reports always print n. Nothing with n<30 becomes a rule change.
- Commits from automation are prefixed `auto:`; human/session commits are not.
