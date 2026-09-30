# Episodic Pivots — project brief (CLAUDE.md)

Owner: Matt Dufton. Purpose: a rules-based, data-evolving workflow for trading Episodic Pivots
(Kullamägi-style catalyst gap-ups). This repo is the canonical store for code, data, briefs and
evaluation notes. Matt's Obsidian folder is a clone of it.

Read this file first in every session. The full PRD lives in the Claude Project "Episodic Pivots"
(doc: EP Workflow v2 — PRD). Rules below are the operative summary.

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
rules/rubric-v2.md   the operative rulebook since 2026-09-30 (gates, entry, stop, sizing, exit)
scripts/             scan.py gates.py catalyst.py brief.py outcomes.py (Python 3, keyless sources)
data/candidates.csv  one row per ticker-day screener hit, machine gates frozen at snapshot time
data/outcomes.csv    forward returns + simulated trade per candidate row (nightly)
data/decisions.csv   Matt's verdicts/fills, timestamped
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
- Intraday 1/5-min bars (ORH/ORL reconstruction): yfinance.
- Catalysts: SEC EDGAR full-text + 8-K Atom (User-Agent header required), api.nasdaq.com news by
  symbol, GlobeNewswire (curl default UA only), PRNewswire search, finviz quote news, Google News RSS.
- Events: stockanalysis `/api/symbol/s/{sym}/earnings` (has `confirmed`), Nasdaq earnings calendar,
  EDGAR "PDUFA" full-text, marketbeat lock-up table.
- Blocked from cloud: Accesswire, businesswire.com, biopharmcatalyst/rttnews (JS), stooq, raw Yahoo.

## Where things run

- Cloud scheduled tasks (Mac may be asleep): 07:45 scan+brief v1, 09:10 brief v2, 10:15 post-open
  snapshot, 16:30 outcomes, Sunday review. They write to this repo and send push/email.
- Mac-linked run (when awake): mirrors brief/log into the Obsidian folder, maintains the
  TradingView watchlist "⚡EP Candidates" via the MCP connector.
- Real-time triggers: Matt's TradingView + the Pine "EP Engine" indicator alert on the watchlist.
  The cloud is never the execution feed.

## Conventions

- Times in ET. Dates ISO. Tickers as EXCHANGE:TICKER in data files, bare ticker in note filenames.
- Every machine field records its basis (e.g. `kq_vol_ratio_basis: premarket|first15|fullday`).
- Weekly reports always print n. Nothing with n<30 becomes a rule change.
- Commits from automation are prefixed `auto:`; human/session commits are not.
