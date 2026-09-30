# Historical EP baseline

Generated 2026-09-29 from 2875 EP-days (1478 tickers). Event = open gap ≥ 8% vs prior close AND day volume ≥ 3× prior 30-day ADV, price ≥ $0.50, cap ≥ $100M today. Returns are from the day-1 open. The simulated trade enters at the day-1 close only when the gap held (close > open), stops at the day-1 low, moves to breakeven after a close ≥ entry + 1 ADR, and exits on the first close below the 10-day SMA. n is shown everywhere; nothing with n < 30 is a conclusion.

## Read (what the numbers say, with the caveats up front)

**Caveats.** Universe = today's listings (survivorship: delisted names are absent); market cap is today's, not the event day's; the simulated trade enters at the day-1 close (an ORH-break entry would be earlier and tighter — this proxy understates the edge of a clean trigger and overstates it when the gap faded intraday and recovered); no slippage or borrow; 17 months (Apr 2025–Aug 2026), mostly one bull regime. Treat every line below as a direction to test live, not a truth.

1. **The gap holding into the close is the strongest single split.** Gap held: +15.5% avg / +6.8% median at 20 days, 42% hold the day-1 low. Gap faded: −6.8% / −9.1%, 16%. Day-1 close in the top 20% of the range beats everything else. This is the mechanical case for Kullamägi's "buy the ORH break, sell the fail" — you only own the ones that are working.
2. **Gate 2 (neglect) is supported.** Neglect ≥85: +6.9% / +1.1%, 33% hold, R +0.12. Neglect <60: +1.6% / −8.7%, 23%, R −0.12. By 3-month pre-gap return the sweet spot is **−30% to 0%** (R +0.29, 31% win); extended (+30–100%) R −0.12 and collapsed (<−30%) R −0.17 are both bad. The rubric's "sideways, not extended, not collapsing" is what the data likes.
3. **Overhead supply is NOT supported as a filter.** Open air (<20% overhead) R +0.01 vs 20–50% overhead R +0.19 and 50–80% R +0.09. Names >50% below their 52-week high have the best average (+14%) but a negative median — fat right tail, not a reliable edge. Keep it logged; do not fail names on it. (Kullamägi never had this rule; the data agrees with him.)
4. **Volume ratio beats the record-day test.** ≥20× ADV: R +0.64, +11.4% avg. Record-day (≥1× of 252-day max) only +0.09 vs +0.04. Gate 3's Kullamägi ratio is the better primary; keep record-day as the "strong" flag, not the pass line.
5. **Huge gaps are worse.** 40%+ gaps: −5.8% avg, −13.7% median, R −0.20. 20–40% is the best bucket (R +0.27). Candidate rule: 40%+ gaps need an extra reason (Tier A + strong volume), else WATCH.
6. **Catalyst matters, in the direction expected.** Earnings 8-K within ±1 day: 30% R-win, 38% hold the low, median +2.4% — the best proxy class. "None" (no filing): median −5.8%, 21% hold. Strong volume + earnings: 45% hold the low, median +4.4%, 32% win. Supports Gate 1 and the Unknown-catalyst cap.
7. **Size: $1–10B beats $100–300M** (median +1.6% vs −4.9%, win 29% vs 23%). Cap is today's cap, so this is partly survivorship (the winners grew), but the direction is worth watching: the $100M floor may be too low, and dropping the $10B ceiling was right.
8. **ADR ≥4% helps average returns, not win rate**; <4% names win more often but move less. Sizing by ADR (the stop cap) handles this better than a filter.
9. **Exits.** 10-day close trail: R +0.07 mean, 26% win. 20-day: +0.17 / 21%. 50-day: +0.27 / 16% (fat tails, ugly median). 1/3 at day-3 close + 10-day trail: +0.09 / **39% win**, same p90. The partial variant is the most livable: near-identical expectancy, much better hit rate. Worth adopting as the default exit, pending live data.
10. **The machine gates work but the unfiltered edge is thin.** Fails a gate: R −0.12. Passes: +0.09. Passes + strong volume: +0.18, 28% win. Strong + earnings: 32% win. With a day-1-close entry that is a marginal system; the live edge has to come from the ORH entry, the tighter stop, and the analyst pass on catalysts — exactly what the live pipeline records and this baseline cannot.

**Proposed for the weekly review to test live** (not shipped): (a) 40%+ gap → WATCH unless Tier A + strong; (b) partial exit as default; (c) overhead stays a logged field, never a fail; (d) watch the $100–300M cap tier's live results before touching the floor.

## Baseline

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all EP-days | 2875 | +5.6% | +0.3% | 31% | 1602 | +0.07 | 26% |

| gap held (close > open) | 1602 | +15.5% | +6.8% | 42% | 1602 | +0.07 | 26% |

| gap faded (close ≤ open) | 1273 | -6.8% | -9.1% | 16% | 0 | — | — |

### Exit variants (gap-held trades)

| Variant | n | avg R | median R | win % | p90 R |
| --- | --- | --- | --- | --- | --- |
| 10-day SMA close trail | 1602 | +0.07 | -0.36 | 26% | +1.54 |
| 20-day | 1591 | +0.17 | -0.46 | 21% | +1.49 |
| 50-day | 1558 | +0.27 | -0.54 | 16% | +1.07 |
| 1/3 at day-3 close + 10-day trail | 1602 | +0.09 | -0.28 | 39% | +1.48 |

### Gap size

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8–12% | 1057 | +7.4% | +1.5% | 32% | 664 | +0.07 | 26% |
| 12–20% | 999 | +6.1% | +0.2% | 29% | 547 | -0.01 | 26% |
| 20–40% | 599 | +5.9% | -0.4% | 32% | 305 | +0.27 | 29% |
| 40%+ | 220 | -5.8% | -13.7% | 27% | 86 | -0.20 | 24% |

### Volume ÷ 30-day ADV (Kullamägi ratio, full day)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3–5× | 1288 | +1.7% | +0.0% | 27% | 674 | +0.02 | 27% |
| 5–10× | 863 | +7.2% | +1.3% | 32% | 517 | -0.11 | 25% |
| 10–20× | 324 | +10.1% | +0.9% | 36% | 206 | +0.09 | 27% |
| 20×+ | 400 | +11.4% | -4.3% | 34% | 205 | +0.64 | 29% |

### Record-volume test (rubric Gate 3 strong pass)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <0.5× of 252-day max | 959 | +5.6% | -2.0% | 27% | 492 | +0.04 | 24% |
| 0.5–1× | 889 | +4.4% | +0.8% | 30% | 501 | +0.07 | 28% |
| ≥1× (record day) | 1027 | +6.8% | +1.3% | 35% | 609 | +0.09 | 27% |

### Neglect score (rubric Gate 2 pass line = 60)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <60 (chart fail) | 368 | +1.6% | -8.7% | 23% | 185 | -0.12 | 22% |
| 60–85 | 292 | +1.4% | -6.2% | 23% | 153 | -0.12 | 22% |
| 85–100 | 2215 | +6.9% | +1.1% | 33% | 1264 | +0.12 | 28% |

### 3-month pre-gap return

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| < −30% | 356 | +3.5% | -4.8% | 25% | 166 | -0.17 | 23% |
| −30–0% | 939 | +8.4% | +0.7% | 33% | 532 | +0.29 | 31% |
| 0–30% | 807 | +5.6% | +0.9% | 34% | 469 | +0.06 | 26% |
| 30–100% (extended) | 540 | +5.5% | +2.2% | 30% | 321 | -0.12 | 22% |
| 100%+ | 233 | -1.6% | -11.5% | 19% | 114 | -0.06 | 21% |

### Overhead supply (hypothesis: not enforced)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <20% (open air) | 1468 | +3.2% | +0.4% | 32% | 835 | +0.01 | 26% |
| 20–50% | 597 | +9.9% | -0.1% | 31% | 327 | +0.19 | 28% |
| 50–80% | 533 | +9.2% | +0.7% | 27% | 293 | +0.09 | 26% |
| 80%+ | 277 | +2.5% | -0.4% | 28% | 147 | +0.06 | 24% |

### Distance from 52-week high at the open

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| < −50% from high | 669 | +14.0% | -1.1% | 27% | 356 | +0.31 | 27% |
| −50–−25% | 717 | +4.7% | -0.1% | 27% | 391 | -0.06 | 22% |
| −25–−5% | 659 | +3.8% | +0.9% | 36% | 378 | +0.11 | 29% |
| within 5% / new high | 830 | +1.2% | +0.3% | 31% | 477 | -0.04 | 27% |

### ADR (20-day) — theStrat Lab found ≥4% helps

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <4% | 631 | +1.7% | +0.7% | 36% | 351 | +0.06 | 31% |
| 4–8% | 1318 | +5.1% | +1.5% | 32% | 776 | +0.07 | 26% |
| 8%+ | 926 | +9.1% | -6.3% | 24% | 475 | +0.07 | 23% |

### Prior high-volume days (≥3× ADV) in 180 sessions

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0–4 | 1617 | +3.3% | +0.7% | 31% | 917 | -0.01 | 27% |
| 5+ | 1258 | +8.7% | -0.6% | 30% | 685 | +0.17 | 26% |

### Day-1 close position in range

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bottom half | 1421 | -3.6% | -7.0% | 16% | 313 | +0.40 | 23% |
| 0.5–0.8 | 784 | +11.5% | +2.8% | 37% | 639 | -0.03 | 25% |
| top 20% | 662 | +18.6% | +10.7% | 54% | 650 | +0.01 | 29% |

### Market cap (today's, proxy)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| $100–300M | 728 | +3.0% | -4.9% | 26% | 373 | +0.06 | 23% |
| $300M–1B | 799 | +4.2% | -1.5% | 30% | 435 | +0.00 | 24% |
| $1–10B | 1027 | +9.0% | +1.6% | 34% | 607 | +0.11 | 29% |
| $10B+ | 321 | +4.4% | +2.7% | 34% | 187 | +0.09 | 30% |

### Catalyst proxy from SEC filings within ±1 day

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| earnings | 1285 | +5.6% | +2.4% | 38% | 781 | +0.05 | 30% |
| agreement | 195 | +2.2% | -0.4% | 28% | 94 | -0.11 | 27% |
| other-8k | 196 | +8.1% | -0.4% | 27% | 106 | +0.22 | 22% |
| filing-other | 521 | +3.8% | -2.2% | 25% | 265 | +0.01 | 21% |
| equity-sale | 79 | +4.6% | +0.0% | 34% | 43 | +0.13 | 26% |
| none | 599 | +7.9% | -5.8% | 21% | 313 | +0.14 | 23% |

### Rubric v2 machine gates (chart pass ∧ volume pass; strong = ≥10× ADV or record day)

| Bucket | n | avg +20d | median +20d | day-1 low held | trades (gap held) | avg R (10-MA) | R win % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fails a gate | 368 | +1.6% | -8.7% | 23% | 185 | -0.12 | 22% |
| passes | 2507 | +6.2% | +0.7% | 32% | 1417 | +0.09 | 27% |
| passes + strong volume | 1082 | +8.0% | +1.2% | 35% | 643 | +0.18 | 28% |
| strong + open air (<20% overhead) | 247 | +7.2% | +2.5% | 38% | 142 | +0.22 | 26% |
| strong + earnings 8-K | 430 | +8.8% | +4.4% | 45% | 297 | +0.16 | 32% |
