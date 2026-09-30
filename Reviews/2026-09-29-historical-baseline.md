# Historical EP baseline

Generated 2026-09-29 from 2476 EP-days (1343 tickers). Event = open gap ≥ 8% vs prior close AND day volume ≥ 3× prior 30-day ADV, price ≥ $0.50, cap ≥ $100M today. Returns are from the day-1 open. The simulated trade enters at the day-1 close only when the gap held (close > open), stops at the day-1 low, moves to breakeven after a close ≥ entry + 1 ADR, and exits on the first close below the 10-day SMA; a bar opening below the stop fills at the open; trades still open at the data end are marked to market. 'avg R winsor ±5' caps each trade at ±5R (the headline mean is driven by ~1% of trades); SE is the standard error of the winsorized mean. n is shown everywhere; nothing with n < 30 is a conclusion.

## Read (what the numbers say — after the independent audit; see 2026-09-29-historical-baseline-audit.md)

**Caveats first.** Universe = today's listings (delisted names absent → optimistic); market cap is today's (a bucket that contains the outcome — do not read size claims off it); the simulated trade enters at the **day-1 close**, not the ORH break, so it is a proxy for "own the ones that held the gap", not for Kullamägi's entry; no slippage; 17 months, mostly one bull regime (2025 R +0.16 / 29% win vs 2026 −0.05 / 23%). About 1% of trades produce most of the raw mean R, so **read the winsorized column and the SE**, not the raw mean.

1. **The base rate is zero or negative.** Buying every EP-day that held its gap and trailing the 10-day: winsorized R −0.09 ± 0.03, 26% win, 44% non-loss. Unfiltered EPs do not pay. The edge, if there is one, is in selection and in the entry — and the entry is exactly what this proxy cannot test. That is the strongest argument for the live pipeline's ORH/ORL records.
2. **Whether the gap held into the close is the biggest split.** Held: +14.0% avg / +6.1% median at 20 days, 41% hold the day-1 low. Faded: −7.2% / −9.3%, 16%. Mechanically, this is the case for "buy only on the break, never before" and for the day-1 stop.
3. **Gate 2 (neglect) is supported, and the line should probably be 85, not 60.** Neglect 85–100: winsorized R −0.05, 27% win, median +1.1%. Neglect 60–85 (−0.24, 22%) is as bad as <60 (−0.18, 21%). By 3-month pre-gap return the only positive cell is **−30% to 0%** (R +0.08 ± 0.07, 31% win, 34% hold the low); extended (+30–100%) −0.22 and collapsed (< −30%) −0.31 both lose. "Sideways, slightly down, not extended, not collapsing."
4. **Overhead supply is not a filter.** Open air (<20%) −0.08; 20–50% −0.01; 50–80% −0.13; 80%+ −0.21. Mild penalty at the extreme, nothing clean. Keep it logged; do not fail names on it (Kullamägi never had this rule).
5. **Volume: the Kullamägi ratio at the extreme is the one volume cell that pays.** ≥20× ADV: winsorized +0.10 ± 0.11, 28% win (raw +0.57 is three trades). 3–20× all negative. Record-day vs not: no separation. Gate 3's pass line at 1× is a screen, not an edge; the "strong ≥10×" flag is where to look.
6. **Gap size: 20–40% is the best band (+0.12 ± 0.09, 28% win); 40%+ is the worst (−0.22, −12.9% median at 20d).** 8–12% gaps look fine on returns (+2.1% median) but not on R. Candidate rule: 40%+ needs Tier A + strong volume or it is WATCH.
7. **Catalyst proxy: earnings is the only robust class.** Earnings 8-K within ±1 day: 30% win, 37% hold the low, median +2.2%; "none" (no filing): 20% win, 20% hold, median −6.2%. Strong volume + earnings: +0.04 ± 0.08, **31% win, 44% hold the low** — the best cell in the table, and it is exactly Kullamägi's "earnings EP". Supports Gate 1 and the Unknown cap.
8. **Market cap: no inference possible** from today's cap (25% of the $100–300M bucket are names that have since fallen >50%). Needs event-day cap before any claim about the $100M floor.
9. **ADR: no filter.** Higher ADR raises average % return but lowers R; the ADR stop cap handles it. Leave as is.
10. **Exits.** 10-day: −0.09 winsorized, 26% win. 20-day −0.10, 21%. 50-day −0.13, 18%. 1/3 at day-3 close + 10-day trail: **−0.05, 39% win, 41% non-loss** — the partial improves the hit rate mostly by converting breakeven stops into small wins; expectancy is unchanged within error. Livable, not an edge. 10-day stays the default; test the partial live.

**Machine gates vs the whole set.** Fails a gate (= neglect <60): −0.18 winsorized, 21% win. Passes: −0.07, 26%. Passes + strong volume: −0.07, 27%. Strong + earnings: +0.04, 31%, 44% hold the low. The gates rank the population correctly and the top cell is the only positive one — with n=286 and SE 0.08, that is "probably a small edge", not proof.

**For the weekly review to test live** (nothing ships without Matt): (a) neglect pass line 60 → 85; (b) 40%+ gap → WATCH unless Tier A + strong; (c) overhead stays logged, never a fail; (d) the strong-volume + earnings cell is the profile to prioritise in the analyst pass; (e) 20×+ ADV as the "strong" threshold of interest. Everything above is a proxy for the real question — what an ORH entry with an OR-low stop earns on the selected names — which only the live outcomes.csv (5-min ORH/ORL) can answer.

## Baseline

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all EP-days | 2476 | +4.9% | +0.1% | 31% | 1421 | +0.03 | -0.09 | ±0.03 | 26% |

| gap held (close > open) | 1421 | +14.0% | +6.1% | 41% | 1421 | +0.03 | -0.09 | ±0.03 | 26% |

| gap faded (close ≤ open) | 1055 | -7.2% | -9.3% | 16% | 0 | — | — | — | — |

### Exit variants (gap-held trades)

| Variant | n | avg R | avg R winsor ±5 | median R | win % | non-loss % | p90 R |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10-day SMA close trail | 1421 | +0.03 | -0.09 | -0.40 | 26% | 43% | +1.46 |
| 20-day | 1421 | +0.15 | -0.10 | -0.48 | 21% | 45% | +1.52 |
| 50-day | 1421 | +0.28 | -0.13 | -0.50 | 18% | 46% | +1.26 |
| 1/3 at day-3 close + 10-day trail | 1421 | +0.05 | -0.05 | -0.32 | 39% | 41% | +1.43 |

### Gap size

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8–12% | 835 | +7.9% | +2.1% | 33% | 552 | +0.06 | -0.13 | ±0.05 | 26% |
| 12–20% | 865 | +3.6% | -0.0% | 28% | 486 | -0.11 | -0.14 | ±0.06 | 24% |
| 20–40% | 567 | +6.1% | -0.4% | 31% | 299 | +0.26 | +0.12 | ±0.09 | 28% |
| 40%+ | 209 | -4.3% | -12.9% | 28% | 84 | -0.22 | -0.22 | ±0.13 | 25% |

### Volume ÷ 30-day ADV (Kullamägi ratio, full day)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3–5× | 1107 | +1.0% | +0.1% | 27% | 600 | -0.02 | -0.11 | ±0.05 | 26% |
| 5–10× | 735 | +5.4% | +1.2% | 32% | 454 | -0.12 | -0.14 | ±0.06 | 25% |
| 10–20× | 276 | +10.6% | +0.0% | 36% | 184 | +0.05 | -0.08 | ±0.10 | 26% |
| 20×+ | 358 | +11.6% | -4.0% | 34% | 183 | +0.57 | +0.10 | ±0.11 | 28% |

### Record-volume test (rubric Gate 3 strong pass)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <0.5× of 252-day max | 700 | +2.6% | -2.8% | 26% | 377 | -0.04 | -0.14 | ±0.07 | 22% |
| 0.5–1× | 814 | +4.3% | +0.8% | 30% | 464 | +0.06 | -0.03 | ±0.06 | 28% |
| ≥1× (record day) | 962 | +7.2% | +1.8% | 35% | 580 | +0.05 | -0.10 | ±0.05 | 27% |

### Neglect score (rubric Gate 2 pass line = 60)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <60 (chart fail) | 332 | +1.8% | -8.7% | 22% | 177 | -0.16 | -0.18 | ±0.09 | 21% |
| 60–85 | 258 | +2.4% | -4.9% | 23% | 138 | -0.19 | -0.24 | ±0.10 | 22% |
| 85–100 | 1886 | +5.8% | +1.1% | 33% | 1106 | +0.09 | -0.05 | ±0.04 | 27% |

### 3-month pre-gap return

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| < −30% | 287 | +3.5% | -5.8% | 23% | 137 | -0.26 | -0.31 | ±0.10 | 22% |
| −30–0% | 786 | +7.5% | +1.0% | 34% | 458 | +0.32 | +0.08 | ±0.07 | 31% |
| 0–30% | 698 | +4.7% | +0.8% | 34% | 415 | +0.03 | -0.09 | ±0.06 | 26% |
| 30–100% (extended) | 488 | +5.2% | +2.3% | 30% | 301 | -0.22 | -0.22 | ±0.07 | 22% |
| 100%+ | 217 | -2.2% | -11.5% | 19% | 110 | -0.10 | -0.14 | ±0.12 | 21% |

### Overhead supply (hypothesis: not enforced)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <20% (open air) | 1323 | +3.3% | +0.3% | 32% | 768 | -0.02 | -0.08 | ±0.04 | 26% |
| 20–50% | 522 | +8.6% | -0.2% | 32% | 295 | +0.10 | -0.01 | ±0.08 | 27% |
| 50–80% | 429 | +7.5% | +1.2% | 28% | 250 | +0.11 | -0.13 | ±0.08 | 26% |
| 80%+ | 202 | +0.5% | -1.3% | 26% | 108 | +0.04 | -0.21 | ±0.11 | 21% |

### Distance from 52-week high at the open

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| < −50% from high | 532 | +12.7% | -2.4% | 27% | 291 | +0.34 | -0.04 | ±0.08 | 26% |
| −50–−25% | 604 | +3.8% | -0.0% | 27% | 338 | -0.14 | -0.20 | ±0.07 | 22% |
| −25–−5% | 572 | +4.1% | +1.3% | 37% | 345 | +0.09 | +0.01 | ±0.07 | 28% |
| within 5% / new high | 768 | +1.1% | +0.3% | 31% | 447 | -0.09 | -0.11 | ±0.06 | 26% |

### ADR (20-day) — theStrat Lab found ≥4% helps

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| <4% | 560 | +1.3% | +0.7% | 37% | 324 | +0.01 | -0.02 | ±0.07 | 31% |
| 4–8% | 1145 | +5.1% | +1.7% | 32% | 694 | +0.06 | -0.05 | ±0.05 | 26% |
| 8%+ | 771 | +7.3% | -7.3% | 23% | 403 | -0.00 | -0.21 | ±0.06 | 22% |

### Prior high-volume days (≥3× ADV) in 180 sessions

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0–4 | 1508 | +3.1% | +0.7% | 31% | 870 | -0.02 | -0.07 | ±0.04 | 27% |
| 5+ | 968 | +7.8% | -0.7% | 29% | 551 | +0.10 | -0.10 | ±0.06 | 24% |

### Day-1 close position in range

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bottom half | 1201 | -3.9% | -7.4% | 15% | 272 | +0.39 | -0.08 | ±0.11 | 22% |
| 0.5–0.8 | 687 | +10.9% | +2.9% | 37% | 571 | -0.07 | -0.12 | ±0.05 | 25% |
| top 20% | 588 | +16.1% | +10.3% | 53% | 578 | -0.04 | -0.06 | ±0.04 | 28% |

### Market cap (today's, proxy)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $100–300M | 479 | +1.9% | -8.6% | 24% | 263 | +0.06 | -0.26 | ±0.08 | 21% |
| $300M–1B | 690 | +3.1% | -1.9% | 29% | 380 | -0.07 | -0.16 | ±0.06 | 23% |
| $1–10B | 991 | +7.8% | +1.5% | 34% | 592 | +0.08 | +0.01 | ±0.06 | 28% |
| $10B+ | 316 | +4.5% | +2.7% | 34% | 186 | +0.05 | +0.02 | ±0.09 | 30% |

### Catalyst proxy from SEC filings within ±1 day

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| earnings | 1186 | +5.4% | +2.2% | 37% | 733 | +0.02 | -0.03 | ±0.05 | 30% |
| agreement | 177 | +2.0% | -0.2% | 28% | 85 | -0.10 | -0.10 | ±0.13 | 29% |
| other-8k | 166 | +7.0% | -0.4% | 27% | 89 | +0.31 | -0.21 | ±0.13 | 21% |
| filing-other | 438 | +0.5% | -3.6% | 24% | 231 | -0.05 | -0.18 | ±0.09 | 20% |
| equity-sale | 75 | +4.8% | +2.1% | 36% | 43 | +0.10 | +0.03 | ±0.22 | 26% |
| none | 434 | +8.4% | -6.2% | 20% | 240 | +0.08 | -0.14 | ±0.09 | 20% |

### Rubric v2 machine gates (chart pass ∧ volume pass; strong = ≥10× ADV or record day)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | avg R winsor ±5 | SE | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fails a gate | 332 | +1.8% | -8.7% | 22% | 177 | -0.16 | -0.18 | ±0.09 | 21% |
| passes | 2144 | +5.4% | +0.7% | 32% | 1244 | +0.06 | -0.07 | ±0.04 | 26% |
| passes + strong volume | 982 | +8.1% | +1.5% | 35% | 594 | +0.12 | -0.07 | ±0.05 | 27% |
| strong + open air (<20% overhead) | 229 | +8.1% | +2.8% | 38% | 135 | +0.21 | -0.06 | ±0.10 | 25% |
| strong + earnings 8-K | 412 | +8.4% | +4.3% | 44% | 286 | +0.13 | +0.04 | ±0.08 | 31% |
