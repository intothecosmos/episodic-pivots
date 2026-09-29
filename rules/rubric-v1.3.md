# EP Gate Rubric

## Gate 1 — Catalyst

Classify what is driving the gap:

**Tier A (strongest)**
- Earnings blowout: big EPS AND revenue beat, ideally accelerating growth, WITH raised guidance
- FDA approval or unambiguously positive Phase 3 data
- Major contract with a named credible counterparty, material to revenue
- Transformative announcement (major partnership, strategic pivot with substance)

**Regulatory sub-ladder** (where FDA/regulatory news lands):
- Full approval or label expansion → Tier A
- Favorable advisory-panel (AdCom) vote → Tier B (strong de-risk, not approval)
- Positive CRL resolution / resubmission acceptance → Tier B
- Prior CRLs on the same asset downgrade one notch and get named on the card
- Single-arm pivotal data supporting the decision → note as a qualifier, not a tier change

**Tier B (decent)**
- Solid beat without a guidance raise
- Positive but early-stage clinical data
- Meaningful but not transformative contract or product news
- Credible activist/strategic-interest news

**Tier C (disqualifying — floor at 1 star, NO TRADE)**
- Share offering, dilution, reverse-split games
- Paid promotion, vague fluffy PR with no numbers
- Pure sympathy gap (sector-mate moved, this company has no news)
- Meme/short-squeeze chatter as the only driver

**Unknown (cap at 3 stars, recheck: true)**
- Real gap + real volume, no identifiable news yet
- Volume can front-run insiders; do not auto-kill, but do not treat as confirmed
- Suggest half risk; re-run Gate 1 when asked or when news appears; upgrade/downgrade the note then

## Gate 2 — Chart (daily)

Judge the chart AS OF the close before the catalyst. The EP move itself is never evidence of "extension" — day-2/day-3 entries are a timing note on the card, not a Gate 2 fail.
Overhead is measured against the 52-WEEK window: supply shelves older than 52 weeks (or >2x current price) get noted but do not fail the gate. Beaten-down former leaders re-igniting on a fundamental inflection can PASS neglect if the pre-catalyst base is months long.

**PASS requires both:**
- Prior neglect: months of sideways or downtrend before the gap; the move is a surprise, not a continuation of hype
- Room overhead: gapping into open air, toward/through 52-week or all-time highs, or clearing the major resistance shelf in one move

**FAIL signals:**
- Stock already up ~100%+ in recent months before this gap (extended, late)
- Gap lands directly beneath a heavy multi-month supply zone

## Gate 3 — Volume

**PASS:** projected full-day volume ≥ largest volume day of the past year (extrapolate: pre-market volume, or first 5–15 minutes × remaining session, is enough for a rough call)
**Strong pass:** projects to largest volume day in multiple years / ever
**FAIL:** projects to merely "above average" — big EPs are volume records, not volume bumps

Quick proxy when full history isn't handy: pre-market volume at a multiple of the 30-day average daily volume (not a fraction of it).
Backfill fallback: full-day volume vs the prior 20-day average; `rel_vol_at_time` is formally nullable when a clean at-time multiple isn't verifiable — grade on the record-day test and say which basis was used.

## Gate 4 — Tradability (binary, no stars can save it)

- Price ≥ $0.50 hard floor (changed from $2.00 by Matt, 2026-08-03)
- Market cap ≥ $100M
- NYSE / NASDAQ / AMEX listing (no OTC)
- Per-ticker judgment above the floor — pass requires ALL of:
  - Spread ≤ ~15% of the planned stop distance (a 1-cent spread on a $1.70
    stock with a 10-cent stop is fine; the same spread on a 3-cent stop is not)
  - Projected full-day dollar volume ≥ ~$10M (exit liquidity)
  - No halt-machine behavior: not a sub-1M microfloat, no reverse-split
    history games, no LULD halt pattern in the pre-market tape
- On sub-$2 names, state the spread-to-stop math explicitly on the card

FAIL any → NO TRADE, grade irrelevant.

## Event Risk (overlay — checked after the gates)

A scheduled binary event within the likely hold window (~2 weeks) — earnings report, PDUFA/regulatory decision, court ruling, lock-up expiration — does not change the star grade, but it caps the verdict at WATCH-until-resolved. Rationale: the EP edge is post-catalyst demand, not event gambling; holding into a coin-flip converts a process trade into a bet. Record the event and date in frontmatter notes and on the card. Once the event resolves, re-evaluate from scratch — a favorable resolution often creates a new, cleaner EP.

## Star grade

- **5★** Tier A catalyst + clean neglect + open air + volume projecting to multi-year record. Rare — a handful per month at most.
- **4★** Tier A/B catalyst, Gates 2–3 pass, one minor blemish (e.g., some overhead, volume "only" a 1-year record).
- **3★** Mixed: Tier B with a chart blemish, or strong everything with Unknown catalyst (the cap). Tradeable at reduced conviction/size.
- **2★** Multiple weaknesses. Watch only.
- **1★** Tier C catalyst or broadly failed gates. Skip, log, move on.

Default action mapping: 4–5★ = TRADE (plan it), 3★ = TRADE small or WATCH (judgment call, say which and why), 1–2★ = NO TRADE.
