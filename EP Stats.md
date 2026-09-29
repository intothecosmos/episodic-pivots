> [!note]- Requires the **Dataview** plugin with "Enable JavaScript queries" on. Tables read the YAML in `Log/`; the pipeline sections read `data/*.csv`. Grades marked `hindsight: true` are excluded from performance statistics.

## Action needed

```dataview
TABLE WITHOUT ID file.link AS Note, verdict, status, event_risk AS "Event", taken
WHERE type = "ep-eval" AND (status = "open" OR status = "watch-event" OR (verdict = "trade" AND taken = null) OR (verdict = "watch" AND status = "evaluated"))
SORT date DESC
```

## Scorecard

```dataviewjs
const pages = dv.pages('"Log"').where(p => p.type == "ep-eval");
const clean = pages.where(p => p.hindsight !== true);
const takenP = pages.where(p => p.taken === true);
const done = takenP.where(p => p.r_multiple != null);
const rs = done.map(p => Number(p.r_multiple)).array();
const n = rs.length, totalR = rs.reduce((a,b)=>a+b,0), wins = rs.filter(r=>r>0).length;
const mean = a => a.length ? (a.reduce((x,y)=>x+y,0)/a.length) : null;
const f = (x, d=1, s="") => x==null ? "—" : (x>0?"+":"") + Number(x).toFixed(d) + s;
const withOut = clean.where(p => p.ret_20d != null);
const graduated = n >= 25 && totalR > 0;
dv.table(["Metric","Value"], [
  ["Evaluated", `${pages.length} (${pages.length - clean.length} hindsight-graded, excluded from stats)`],
  ["Taken", `${takenP.length} — selectivity ${pages.length ? (100*takenP.length/pages.length).toFixed(0) : "—"}%`],
  ["Completed trades", `${n} · win rate ${n ? (100*wins/n).toFixed(0)+"%" : "—"} · total R ${f(totalR,2)}`],
  ["Graduation to 0.5% risk", graduated ? "UNLOCKED" : `LOCKED — ${n}/25 completed, total R ${f(totalR,2)}`],
  ["Avg +20d return, all evaluated (from day-1 open)", f(mean(withOut.map(p=>Number(p.ret_20d)).array()), 1, "%")],
  ["Avg simulated rule trade (ORH → 10-MA close), all evaluated", f(mean(clean.where(p=>p.sim_r10!=null).map(p=>Number(p.sim_r10)).array()), 2, "R")],
  ["Day-1 low held", `${clean.where(p=>p.d1_low_held===true).length} of ${clean.where(p=>p.d1_low_held!=null).length}`],
]);
```

## Does the grade predict? (excludes hindsight)

```dataviewjs
const pages = dv.pages('"Log"').where(p => p.type == "ep-eval" && p.hindsight !== true && p.ret_20d != null);
const mean = a => a.length ? a.reduce((x,y)=>x+y,0)/a.length : null;
const f = (x, d=1, s="") => x==null ? "—" : (x>0?"+":"") + Number(x).toFixed(d) + s;
const rows = [];
for (const g of [5,4,3,2,1]) {
  const s = pages.where(p => Number(p.grade) === g);
  if (!s.length) continue;
  rows.push([`${"★".repeat(g)}${"☆".repeat(5-g)}`, s.length,
    f(mean(s.map(p=>Number(p.ret_5d)).array()),1,"%"), f(mean(s.map(p=>Number(p.ret_20d)).array()),1,"%"),
    `${s.where(p=>p.d1_low_held===true).length}/${s.length}`, f(mean(s.where(p=>p.sim_r10!=null).map(p=>Number(p.sim_r10)).array()),2,"R")]);
}
dv.table(["Grade","n","avg +5d","avg +20d","day-1 low held","avg sim R (10-MA)"], rows);
```

## By catalyst tier (excludes hindsight)

```dataviewjs
const pages = dv.pages('"Log"').where(p => p.type == "ep-eval" && p.hindsight !== true && p.ret_20d != null);
const mean = a => a.length ? a.reduce((x,y)=>x+y,0)/a.length : null;
const f = (x, d=1, s="") => x==null ? "—" : (x>0?"+":"") + Number(x).toFixed(d) + s;
const rows = [];
for (const t of ["A","B","C","unknown"]) {
  const s = pages.where(p => String(p.catalyst_tier) === t);
  if (!s.length) continue;
  rows.push([t, s.length, f(mean(s.map(p=>Number(p.ret_20d)).array()),1,"%"), `${s.where(p=>p.d1_low_held===true).length}/${s.length}`,
    f(mean(s.where(p=>p.sim_r10!=null).map(p=>Number(p.sim_r10)).array()),2,"R")]);
}
dv.table(["Tier","n","avg +20d","day-1 low held","avg sim R (10-MA)"], rows);
```

## All evaluations

```dataview
TABLE WITHOUT ID file.link AS Note, grade AS "★", verdict, catalyst_tier AS Tier, status, ret_5d AS "+5d %", ret_20d AS "+20d %", sim_r10 AS "sim R", d1_low_held AS "D1 low held", hindsight
FROM "Log"
WHERE type = "ep-eval"
SORT date DESC
```

## Completed trades

```dataview
TABLE WITHOUT ID file.link AS Note, entry, stop, exit_price, exit_date, r_multiple AS R, mistakes
FROM "Log"
WHERE type = "ep-eval" AND taken = true AND r_multiple != null
SORT exit_date DESC
```

## Pipeline: every screener hit (data/candidates.csv → data/outcomes.csv)

```dataviewjs
try {
  const cands = await dv.io.csv("data/candidates.csv");
  const outs = await dv.io.csv("data/outcomes.csv");
  const byKey = {};
  for (const o of outs) byKey[`${o.ticker}|${o.date}`] = o;
  const seen = new Set(); const rows = [];
  for (const c of cands.array()) {
    const k = `${c.ticker}|${c.date}`; if (seen.has(k) || !c.ticker) continue; seen.add(k);
    const o = byKey[k] || {};
    rows.push([c.date, c.ticker, c.gap_pct, c.kq_vol_ratio, c.record_vol_ratio, c.neglect_score, c.overhead_pct,
               c.gate_volume_auto, c.gate_chart_auto, c.gate_tradability_auto, o.ret_5d ?? "—", o.ret_20d ?? "—", o.sim_r10 ?? "—", o.d1_low_held ?? "—"]);
  }
  rows.sort((a,b) => a[0] < b[0] ? 1 : -1);
  dv.paragraph(`${rows.length} candidate-days on file · ${rows.filter(r => r[11] !== "—").length} with 20-day outcomes`);
  dv.table(["Date","Ticker","Gap%","×ADV","Rec","Neglect","Overhead%","Vol","Chart","Tradable","+5d","+20d","sim R","D1 low"], rows.slice(0, 60));
} catch (e) { dv.paragraph("No pipeline data yet (data/candidates.csv fills from the first scheduled run)."); }
```
