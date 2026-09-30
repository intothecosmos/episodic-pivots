# Historical EP baseline

Generated 2026-09-29 from 2476 EP-days (1343 tickers). Event = open gap ≥ 8% vs prior close AND day volume ≥ 3× prior 30-day ADV, price ≥ $0.50, cap ≥ $100M today. Returns are from the day-1 open. The simulated trade enters at the day-1 close only when the gap held (close > open), stops at the day-1 low, moves to breakeven after a close ≥ entry + 1 ADR, and exits on the first close below the 10-day SMA; a bar opening below the stop fills at the open; trades still open at the data end are marked to market. 'avg R winsor ±5' caps each trade at ±5R (the headline mean is driven by ~1% of trades); SE is the standard error of the winsorized mean. n is shown everywhere; nothing with n < 30 is a conclusion.

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
