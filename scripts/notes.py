"""notes.py — housekeeping for Log notes.

  python notes.py headers     # add/refresh the auto header callout under the frontmatter
  python notes.py hindsight TICKER DATE ...   # set hindsight: true on given notes
  python notes.py set TICKER DATE key value   # set a frontmatter key (append-only contract)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from common import LOG

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
STARS = {1: "★☆☆☆☆", 2: "★★☆☆☆", 3: "★★★☆☆", 4: "★★★★☆", 5: "★★★★★"}


def parse_fm(fm: str) -> dict:
    d = {}
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z_][\w]*):\s*(.*?)\s*(#.*)?$", line)
        if m:
            v = m.group(2).strip().strip('"')
            d[m.group(1)] = v
    return d


def header_block(d: dict) -> str:
    try:
        g = int(float(d.get("grade") or 0))
    except Exception:
        g = 0
    verdict = (d.get("verdict") or "").upper().replace("-", " ")
    status = d.get("status", "")
    kind = {"TRADE": "success", "WATCH": "warning", "NO TRADE": "failure"}.get(verdict, "note")
    taken = d.get("taken", "")
    tail = ""
    if taken in ("true", "True"):
        r = d.get("r_multiple", "")
        tail = f" · taken · {status}{(' ' + (('+' if not r.startswith('-') else '') + r + 'R')) if r else ''}"
    elif status and status != "evaluated":
        tail = f" · {status}"
    hind = " · ⚠ hindsight-graded, excluded from stats" if d.get("hindsight") in ("true", "True") else ""
    gates = " · ".join(f"{k.split('_')[1].title()} {d.get(k,'?')}" for k in ("gate_chart", "gate_volume", "gate_tradability"))
    ev = f"\n> Event risk: {d['event_risk']}" if d.get("event_risk") else ""
    return ("<!-- header:auto -->\n"
            f"> [!{kind}] {d.get('ticker','?')} — {STARS.get(g, '?')} {g}/5 — {verdict}{tail}{hind}\n"
            f"> Tier {d.get('catalyst_tier','?')} · gap {d.get('gap_pct') or '—'}% · rel vol {d.get('rel_vol_at_time') or '—'}× · "
            f"cap ${d.get('mkt_cap_m') or '—'}M · float {d.get('float_m') or '—'}M · {gates}\n"
            f"> {d.get('catalyst','')}{ev}\n"
            "<!-- /header:auto -->\n")


def refresh_headers():
    for p in sorted(LOG.glob("*.md")):
        txt = p.read_text()
        m = FM_RE.match(txt)
        if not m:
            continue
        d = parse_fm(m.group(1))
        block = header_block(d)
        body = txt[m.end():]
        if "<!-- header:auto -->" in body:
            # lambda: catalyst text may contain backslashes; `\n?`: tolerate a missing trailing newline
            body = re.sub(r"<!-- header:auto -->.*?<!-- /header:auto -->\n?", lambda _: block, body, flags=re.S)
        else:
            body = block + "\n" + body.lstrip("\n")
        # collapse the original monospace verdict card into a foldable callout (content untouched)
        if "> [!abstract]- Original verdict card" not in body:
            body = re.sub(r"(## Evaluation\n(?:(?!```)(?!## ).)*?)```\n(.*?)```\n",
                          lambda mm: mm.group(1) + "> [!abstract]- Original verdict card\n> ```\n" +
                          "".join("> " + l + "\n" for l in mm.group(2).splitlines()) + "> ```\n",
                          body, count=1, flags=re.S)
        p.write_text(f"---\n{m.group(1)}\n---\n{body}")
        print("header:", p.name)


def set_key(ticker: str, date: str, key: str, val: str):
    p = LOG / f"{date} {ticker}.md"
    txt = p.read_text()
    m = FM_RE.match(txt)
    fm = m.group(1)
    if re.search(rf"^{key}:", fm, re.M):
        fm = re.sub(rf"^{key}:.*$", f"{key}: {val}", fm, flags=re.M)
    else:
        fm += f"\n{key}: {val}"
    p.write_text(f"---\n{fm}\n---\n{txt[m.end():]}")
    print(f"{p.name}: {key} = {val}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "headers":
        refresh_headers()
    elif a and a[0] == "hindsight":
        pairs = a[1:]
        for i in range(0, len(pairs), 2):
            set_key(pairs[i], pairs[i + 1], "hindsight", "true")
    elif a and a[0] == "set":
        set_key(a[1], a[2], a[3], a[4])
