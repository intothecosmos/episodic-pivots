# EP Rubric v2 — OPERATIVE from 2026-09-30 (signed off by Matt 2026-09-29; v1.3 kept as rules/rubric-v1.3.md for reference)

Tags: **[adopt]** = from Kullamägi's own material, missing from v1.3. **[hyp]** = our rule or a
softer claim; logged as a field and tested, not enforced blindly.

## Gate 0 — Regime [adopt]
- QQQ 10-day SMA > 20-day SMA and both rising → green: full rules.
- Otherwise red: no new EPs, or half size at most. Recorded on every candidate row (`regime`).

## Screen (07:45 ET, cloud)
- Premarket change ≥ 8% (10%+ flagged) · premarket volume ≥ 0.5× 30-day ADV · market cap ≥ $100M
  (no ceiling [adopt]) · price ≥ $0.50 · NYSE/NASDAQ/AMEX · common stock.

## Gap-size overlay [hyp, adopted 2026-09-29 from the historical baseline, n=209]
- Gaps ≥ 40% are WATCH unless the catalyst is confirmed Tier A AND volume is strong (≥10× ADV or
  record day). Historically the 40%+ band had the worst 20-day median (−12.9%) and R (−0.22).

## Gate 1 — Catalyst (unchanged)
- Tier A / B / C ladder incl. regulatory sub-ladder. Tier C = 1★ no trade [hyp — tracked].
- Unknown = cap 3★, `recheck: true`, half risk.

## Gate 2 — Chart, judged pre-catalyst
- Neglect [adopt, computed]: `neglect_score` from 3/6-month return ex-gap, base tightness,
  distance from 52-week high. No big multi-month run into the gap.
- Overhead supply [hyp]: `overhead_pct` recorded (volume-weighted share of last 252 sessions
  closing above today's price). Not an automatic fail in v2.

## Gate 3 — Volume [adopt + hyp]
- `kq_vol_ratio` = volume by 9:45 (or premarket) ÷ 30-day ADV. Pass ≥ 1. Strong ≥ 10.
- `record_vol_ratio` = projected full-day ÷ largest day in prior 252 sessions. Strong ≥ 1.
- Both recorded with basis. Pass on the first; the second is the "strong pass".

## Gate 4 — Tradability (unchanged)
- Price ≥ $0.50 · cap ≥ $100M · listed · spread ≤ 15% of stop distance · projected dollar
  volume ≥ $10M · no halt-machine behaviour. Any fail → no trade.

## Entry (unchanged, + timing note)
- Break of the opening-range high: 1-min if it gaps over the level and runs; 5-min standard;
  60-min for slow large gaps. Never premarket, never before the trigger, never chase below it.
- Full size in one buy. Preferred structure: gap → fade → higher lows → ORH reclaim [adopt].

## Stop [adopt]
- Opening-range low (or low of day). Market stop, not mental.
- If stop distance > 1.0× ADR: skip, or size down so dollar risk is unchanged (1.5× tested as alt).
- Never widen a stop.

## Sizing
- Risk 0.25% of net-liq equity; 0.5% only after ≥25 completed trades with positive total R;
  never > 1%.
- Position ≤ 1% of 30-day ADV [adopt]. ≤ 30% of account in one name overnight [adopt].

## Exit [adopt — new section]
- Day 1: the only exit is the stop. No discretionary intraday selling.
- After a close ≥ entry + 1 ADR: stop to breakeven.
- Trail: exit on the first daily CLOSE below the **10-day SMA** (default). 20-day is the
  documented alternative for slower, larger names; 20 and 50 are scored alongside 10 in the
  nightly simulation so the data can argue for a switch. Intraday violations don't count.
- Optional tested variant: sell 1/3 into strength day 3–5, trail the rest.
- Never hold into a scheduled binary (earnings, PDUFA, court, lock-up) without a large cushion.
- Mechanism: Pine "EP Engine" alerts on the ⚡EP Candidates watchlist / SMA 10/20 Cross & Trail.

## Event risk (unchanged)
- Known binary inside ~2 weeks caps the verdict at WATCH until it resolves.

## Star grade and action mapping (unchanged from v1.3)
- 5★ rare; 4–5★ TRADE; 3★ TRADE small or WATCH (say which); 1–2★ NO TRADE.

## Logging
- Machine grade + all gate fields frozen at 07:45/09:10 (`frozen_at`). Matt's verdict is a separate,
  timestamped field. `hindsight: true` excludes a grade from stats.
