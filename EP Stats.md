# EP Stats

> [!note]
> The **Dataview** community plugin must be enabled for these tables to render (and "Enable JavaScript queries" in Dataview settings for the Summary block).

## All evaluations

```dataview
TABLE ticker, date, grade, verdict, status
WHERE type = "ep-eval"
SORT date DESC
```

## Completed trades (R-multiples)

```dataview
TABLE ticker, date, entry, stop, exit_price, exit_date, r_multiple, mistakes
WHERE type = "ep-eval" AND taken = true AND r_multiple != null
SORT exit_date DESC
```

## Summary

```dataviewjs
const pages = dv.pages().where(p => p.type == "ep-eval");
const evaluated = pages.length;
const takenPages = pages.where(p => p.taken === true);
const taken = takenPages.length;
const completed = takenPages.where(p => p.r_multiple !== null && p.r_multiple !== undefined);
const rs = completed.map(p => p.r_multiple).array();
const n = rs.length;
const totalR = rs.reduce((a, b) => a + b, 0);
const wins = rs.filter(r => r > 0).length;
const winRate = n ? (100 * wins / n).toFixed(0) + "%" : "—";
const selectivity = evaluated ? (100 * taken / evaluated).toFixed(0) + "%" : "—";
const open = pages.where(p => p.status == "open").length;
const graduated = n >= 25 && totalR > 0;

dv.table(["Metric", "Value"], [
  ["Evaluated", evaluated],
  ["Taken", taken + "  (selectivity " + selectivity + " — lower is more selective)"],
  ["Open positions", open],
  ["Completed trades", n],
  ["Win rate", winRate],
  ["Total R", totalR.toFixed(2)],
  ["Graduation to 0.5% risk", graduated
    ? "UNLOCKED (≥25 completed, positive total R)"
    : "LOCKED — " + n + "/25 completed trades, total R " + totalR.toFixed(2) + " (needs ≥25 and positive total R)"],
]);
```
