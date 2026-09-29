# episodic-pivots

Rules-based Episodic Pivot workflow: scheduled scan → machine gates → catalyst evidence → brief →
nightly forward-return tracking → (weekly) evidence report. Brief: `CLAUDE.md`. Rulebook:
`rules/rubric-v2.md` (pending sign-off; v1.3 alongside). Note contract: `rules/log-template-v2.md`.

## Run by hand

```bash
pip install --break-system-packages tradingview-screener yfinance requests pyyaml
cd scripts
python run_morning.py                    # premarket scan → Briefs/YYYY-MM-DD.md (label v1)
python run_morning.py --label v2         # 09:10 refresh
python run_morning.py --mode regular     # after the open, or an evening dry run
python outcomes.py                       # forward returns + simulated trades for every candidate/Log note
python outcomes.py AUTL                  # one ticker
python notes.py headers                  # refresh the auto header callouts in Log/
python notes.py set TICKER DATE key val  # set a frontmatter key (append-only contract)
```

## What each script does

| Script | Reads | Writes |
| --- | --- | --- |
| `scan.py` | TradingView scanner (15-min delayed) | list of hits + Gate 0 regime (QQQ/SPY 10/20 SMA from daily bars) |
| `gates.py` | daily bars (stockanalysis → nasdaq → yfinance), earnings JSON | `data/candidates.csv` — frozen machine gates with basis per field |
| `catalyst.py` | SEC submissions, Nasdaq news, GlobeNewswire, finviz, Google News | evidence + heuristic pre-tier (A?/B?/C?/MA-target/unknown) |
| `brief.py` | the above | `Briefs/DATE.md`, `Briefs/watchlist-DATE.txt`, `Briefs/DATE.grades.json` |
| `outcomes.py` | daily + 5-min bars | `data/outcomes.csv`, Outcome block + `ret_5d/ret_20d/sim_r10/d1_low_held` keys in Log notes |
| `notes.py` | Log notes | header callouts, hindsight flags, key edits |

## Scheduled runs (cloud, ET)

| Time | Task | Commit prefix |
| --- | --- | --- |
| 07:45 Mon–Fri | scan + brief v1 + analyst pass + watchlist + push/email | `auto: brief v1` |
| 09:10 Mon–Fri | brief v2 refresh | `auto: brief v2` |
| 16:35 Mon–Fri | outcomes + note updates | `auto: outcomes` |

Matt's Obsidian vault is a clone of this repo (Obsidian Git auto-pull). Grades are frozen at
snapshot time; the analyst pass appends to the brief and never edits `candidates.csv`.

## Data notes

- All sources are keyless. `stockanalysis.com` needs a full Chrome User-Agent; SEC needs a named
  User-Agent; GlobeNewswire only answers curl's default UA. `.cache/` holds 6-hour history caches.
- The scanner's `gap` = open vs prior close; `premarket_change` = premarket last vs prior close and
  freezes at 09:30. `record_vol_ratio` compares volume-so-far to the largest day in the prior 252
  sessions — read it with its basis (`premarket` / `intraday HH:MM` / `fullday`).
- Simulated trades: entry = 5-min ORH (yfinance, ≤60 days old) else day-1 open; stop = ORL else day-1
  low; breakeven after a close ≥ entry + 1 ADR; exit on first close below the 10/20/50-day SMA.
  It compares rules against each other; it is not Matt's P&L.
