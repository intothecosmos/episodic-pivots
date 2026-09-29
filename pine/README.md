# Pine scripts

Two Pine v6 scripts sharing one rule set (rules/rubric-v2.md). They are not yet compiled in
TradingView — paste, compile, and report any error line; Pine can only be validated there.

## EP Engine (indicator) — the rules on the chart, alerts in real time

1. TradingView → Pine Editor → New → paste `EP_Engine.pine` → **Add to chart**. Save as "EP Engine".
2. Use it on a **1-min or 5-min** chart. Daily context (gap, ADV, record volume, neglect, ADR, trail
   MA, QQQ regime) is pulled with `request.security`, so the chart timeframe only affects the opening
   range and the intraday signals.
3. Table (top-right by default): Gate 0 regime, gap %, volume ÷ ADV30, volume ÷ 252-day max, 3m/6m
   pre-gap return, distance to 52-week high, OR high/low with stop-vs-max-ADR check, ADR and trail MA.
   Green = pass, red = fail, grey = not applicable yet. Status cell: waiting → SETUP VALID → IN TRADE → STOPPED.
4. Signals: green triangle = ORH break on a valid setup (grey = ORH break but a gate failed);
   red ✕ = stop hit; orange ● = daily close below the trail MA (fires in the last 10 minutes).
5. **One alert covers everything.** Right-click the chart → Add alert → Condition: *EP Engine* →
   *Any alert() function call* → Options: once per bar → set it on the **⚡EP Candidates watchlist**
   (the "symbol" dropdown accepts a watchlist on Premium/Ultimate; otherwise one alert per symbol).
   Alert messages are JSON: `{"ticker","event","price","orh","orl","gap","volx","valid"}` with events
   `setup_valid`, `orh_break`, `orh_break_invalid`, `stop_hit`, `trail_break_10|20|50`, `day3to5_partial_window`.

Inputs mirror the rubric: gap ≥ 8, volume ratio ≥ 1 (strong ≥ 10), 3-month pre-gap return ≤ 30%,
OR minutes (1/5/15/30/60), max stop 1.0× ADR, trail MA 10/20/50, breakeven after +1 ADR close.

## EP Strategy (strategy) — backtest the same rules

1. Paste `EP_Strategy.pine` → Add to chart on a **5-min** chart → open the Strategy Tester tab.
2. It arms a stop-market buy at the OR high when the OR completes on a valid setup (day 1 only),
   sizes by `equity × risk% ÷ (ORH − ORL)`, stops at the OR low, moves to breakeven after a daily
   close ≥ entry + 1 ADR, exits on the first daily close below the trail MA. Toggle "Sell 1/3 at day-3
   close" to test the partial variant. Change the trail MA input to compare 10 / 20 / 50.
3. Bars available depend on the TradingView plan (Premium ≈ 3 months of 5-min bars). For older
   EPs use the Python `outcomes.py` simulation, which reconstructs the same rules from daily data.

Pine cannot screen the market or know a catalyst — that stays in the Python pipeline. What it
adds is real-time triggering and per-symbol rule testing on your own chart.
