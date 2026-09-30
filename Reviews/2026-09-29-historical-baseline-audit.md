# Audit — Historical EP baseline (2026-09-29)

Independent check of `scripts/historical.py`, `scripts/stats.py` and `Reviews/2026-09-29-historical-baseline.md`. Nothing was modified; all numbers below were recomputed from `.cache/hist_bars.pkl` and `data/historical_eps.csv` (2,875 events, 1,602 gap-held trades).

## 1. Lookahead

`_events_for` is clean. `adv` = `bars[i-30:i]`, `maxv`/`hi52`/`overhead` = `prior[-252:]`, `w63`/`r3`/`r6`/`tight` = prior closes, `adr` = `prior[-20:]`, `hv180` = `prior[-180:]`. Forward fields use `bars[i+1:i+21]` and `bars[i+k]["c"]`; `d1_low_held` compares `fut` lows to `b["l"]`; loop bound `n-21` guarantees `bars[i+20]`. No leakage.

Definitional notes, not leaks:
- `overhead` references the day-1 **open** — appropriate (known at screen time). But 810 rows (28%) have `overhead == 0`, so "<20% open air" is mostly "opening above every close of the past year", confounding claim 3.
- The event is conditioned on full-day volume and `gap_held` on the day-1 close, so the "from the open" return columns use information unavailable at the open. Fine for the close-entry sim; not what a 09:45 screen sees.
- `hv180` compares old volumes against *today's* ADV (mixed basis). The rubric says neglect includes distance from 52-week high; the code has no such term.

## 2. Recompute (random.seed(7): PRCT 2026-04-30, ONDS 2025-06-09, STLN 2026-08-07, HOFT 2026-06-11, NTNX 2026-02-26)

All ten fields (gap_open_pct, vol_x_adv30, record_vol_ratio, ret_5d, ret_20d, mfe_20d, d1_low_held, neglect_score, gap_held, sim_r10) match the CSV exactly on all five rows. HOFT is the only gap-held one: 0.0R both ways (breakeven stop). No mismatches.

## 3. Simulation sanity

- Stop-before-MA ordering is conservative and correct; the breakeven move applies from the *next* bar (stop checked against old `cur` first) — correct.
- `_sma(closes, n, j)` includes bar j's close: exit on "close j < SMA10 through close j", filled at that close. Standard.
- **Fill assumption is not conservative.** Stops always fill at `cur`. 81 of 940 stop exits occurred on a bar that *opened below* the stop; filling at the open costs −155R. Mean R falls from **+0.067 to −0.03** — one assumption flips the headline's sign.
- 306 trades (19%) are exact 0.0R breakeven stops; see claim 9.
- Still-open exclusion: sim_r10 0, sim_r20 11, sim_r50 44 trades. The excluded are the winners: sim_r20 exclusions average +45.8% at +20d vs +7.7% for resolved trades in the same window; sim_r50 +31.0% vs +6.9%. Marked to last close they carry +4.78R and +3.10R; including them moves r20 +0.175 → +0.206, r50 +0.273 → +0.351. Moderate bias against the slower trails.
- The sim ignores the rubric's "stop distance > 1.0× ADR: skip or size down": 1,267 of 1,602 trades (79%) violate it. The compliant subset (n=335) is +0.43R mean, −1.0 median, +0.03 winsorized — all five largest R in the set live here (tight stop → huge R).

## 4. Event definition

- Per month: 71 (Apr-25, partial) to 259 (May-26); no month above 9%. The regime split matters more: 2025 events R +0.159 / win 29% (n=885); 2026 R −0.047 / 23% (n=717); +20d avg +8.1% vs +2.6%.
- Tickers: 1,478; 769 with one event. Top: ASST, DGXX, AEHL, SRFM (10 each), USAR 9, SBET/CRML/TII/FXHO/ANNA/BYND/SVRN/VIVO 8. 81 tickers with ≥5 events supply 496 rows (17%). 338 events (12%) fall within 20 sessions of a prior event on the same ticker; de-duplicating moves mean R only +0.067 → +0.069.
- Data problems: 65 events have a zero-volume bar in the prior 30 (ADV deflated; nearly all dual-class lines — WSO.B, MOG.B, TAP.A — showing `vol_x_adv30` 30.0 on nothing); 204 have prior-30 median volume < 20k shares; **380 (13%) had day-1 dollar volume < $10M**, a rubric Gate 4 fail; 58 have prior close < $1; 57 tickers show a >3× day-over-day close (178 events) — spot-checked as genuine moves (PRAX +176%, SBET +405%, KRSA +250%), not split artefacts (yfinance is split-adjusted). Suggested exclusions: $ volume < $10M (380), zero-volume bar in prior 30 (65), prior close < $1 (58).

## 5. stats.py

`summarize()` matches its headers: avg/median +20d over all rows, `d1_low_held` % over rows with a value (all), trade count and R stats over `gap_held == True` rows with non-null `sim_r10`. Edges are `lo <= v < hi`, non-overlapping, and every table covers its range (`[0,101)`, `±INF`, `[0,1.01)`). p90 index is fine.

Gates: `vol_x_adv30 ≥ 1` is trivially true (0 rows below 3), so **"fails a gate" ≡ neglect < 60, exactly 368 = 368** — it is a neglect table. "Strong" is full-day ≥10× or record day (453 of 1,082 qualify via record day only); the rubric's strong is ≥10× *by 09:45*, far stricter. The baseline's "strong" is not the rubric's.

## 6. Claims

Robustness reference: winsorizing `sim_r10` at 5R turns the overall +0.067 into **−0.048**; removing the top 5 trades gives −0.015; the top 16 trades (1%) sum to 251R against a total of 107.5R. SE of mean R is 0.054, so +0.067 is 1.2 SE from zero.

1. **Gap held** — SUPPORTED as description (+15.5/+6.8% vs −6.8/−9.1%), but it conditions on the day-1 return itself. "Top-20% close beats everything" holds from the open, not for the trade: top-20% close R +0.007 (n=650); bottom-half-but-held +0.40 raw / −0.015 winsorized (the five largest R are all bottom-half closes with tiny stops). OVERSTATED for the sim.
2. **Neglect** — SUPPORTED in direction (<60: −0.125, winsor −0.148; 85–100: +0.118, winsor −0.019). But 60–85 (R −0.119, n=153) is indistinguishable from <60; the data argues for a pass line at 85, not 60. −30–0% 3-month bucket is the only one positive after winsorization (+0.083).
3. **Overhead not a filter** — SUPPORTED as "do not fail on it". OVERSTATED as "data agrees overhead is harmless": winsorized, 50–80% (−0.111) and 80%+ (−0.123) are the two worst buckets, and the <20% bucket is 55% overhead-zero (new-high names), so the comparison is confounded with extension.
4. **Volume ratio beats record day** — SUPPORTED in direction, OVERSTATED in magnitude. 20×+ R +0.64 is SLNH (40.8R), CVGI (24.7R), MGRT (22.6R); winsorized +0.142, median 0.00. Record ≥1 vs <0.5: +0.086 vs +0.037 raw, −0.057 vs −0.074 winsorized — no separation.
5. **40%+ gaps worse** — SUPPORTED: R −0.20 (n=86, unchanged by winsorizing), median +20d −13.7% (n=220). 20–40% is the only gap bucket positive after winsorizing (+0.128).
6. **Earnings catalyst** — SUPPORTED: 30% win, 38% hold, median +2.4%; winsorized +0.002 vs "none" −0.079. Strong+earnings 45% hold / 32% win / winsor +0.076 — the most robust cell in the report.
7. **Cap** — WRONG as an inference. The bucket key contains the outcome: 25% of $100–300M events (183/728) are down >50% since the event vs 7% (71/1027) in $1–10B; 11% of $1–10B events are up >2× vs 6%. Direction is uninterpretable until event-day cap (shares × prior close) is used.
8. **ADR ≥4% helps averages** — OVERSTATED. True for the unfiltered from-open average (+1.7/+5.1/+9.1%), but the trade sim reverses: winsorized R <4% +0.029, 4–8% −0.027, 8%+ −0.140; 8%+ median +20d −6.3%.
9. **Partial exit 39% win** — OVERSTATED. 203 of the 212 trades that flip to "win" are exact 0.0R breakeven stops turned slightly positive by the day-3 leg; 171 of 628 partial wins are ≤0.25R. Non-loss (R≥0) is already 45% under the plain 10-SMA. The leg is sold regardless of price — 421 of 1,094 day-3 legs sold *below* entry — not the rubric's "into strength". Expectancy unchanged (+0.093 vs +0.067).
10. **Gates work, edge thin** — OVERSTATED. Fails are the worst bucket under every treatment (SUPPORTED); "passes" is +0.092 raw but −0.035 winsorized and −0.03 with open fills on gap-throughs. The unfiltered edge is not thin, it is zero or negative; only strong+earnings survives.

## 7. Other methodological issues

- Tail concentration is the dominant problem; every positive R cell needs a winsorized column beside it.
- A minimum-risk filter barely matters (risk ≥2%: +0.053, n=1,565; ≥3%: +0.041) — the outliers are genuine 2–7% stops on 3–5× movers, not micro-denominators. Winsorize; don't filter.
- Universe is today's 3,947 listings: delisted names (the worst EP outcomes) are absent. Unquantifiable; direction is optimistic.
- No slippage, spread, borrow, halts; 380 events fail the rubric's own $10M gate.
- 17 months, one regime, and the two halves disagree in sign.
- Catalyst proxy is ±1 calendar day of an 8-K; 599 "none" rows include foreign issuers and news without filings.

## Fixes recommended (ranked)

1. Add winsorized (5R) and median R columns to every table; report SE of mean R. Restate claims 4, 8, 10 against them.
2. Fill stops at `min(cur, open)` on gap-through bars; report both.
3. Apply Gate 4 in the event filter (day-1 $ volume ≥ $10M; prior close ≥ $1); drop tickers with zero-volume bars in the prior 30.
4. Replace `mkt_cap_m_now` with event-day cap (shares × prior close); mark claim 7 unresolved until then.
5. Mark still-open trades to the last close (flag `open: true`) instead of dropping them.
6. Rename "Rubric v2 machine gates" to "neglect ≥ 60 / < 60" until a 09:45 volume proxy exists; note "strong" is full-day.
7. Partial exit: gate the day-3 sale on close > entry; report breakeven stops as their own count.
8. Add a regime column (2025 / 2026, or QQQ 10>20 SMA at event).
9. Print the same-ticker-overlap count and a deduplicated baseline row.
10. Add the 52-week-high term to `neglect_score` or fix the rubric text; record `hv180`'s mixed basis.
