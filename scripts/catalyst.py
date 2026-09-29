"""catalyst.py — gather same-day catalyst evidence for a ticker from keyless sources and
propose a HEURISTIC tier. The final Tier A/B/C/Unknown call is made by Claude in the run
(or by Matt); this module just brings the evidence to one place.

Sources (in order of authority):
  1. SEC EDGAR submissions (8-K / 6-K / 425 / S-1 / 424B in the last 3 days) — the filing is the fact
  2. Nasdaq news-by-symbol (RTTNews/Benzinga/Reuters headlines, timestamped)
  3. GlobeNewswire keyword search (company PRs)
  4. finviz quote-page news list
  5. Google News RSS (last resort, noisy)
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys

from common import CHROME_UA, SEC_UA, cache_json, get, today_et

TIER_A = [r"fda approv", r"approval of", r"approves", r"rais(es|ed|ing) .{0,25}(guidance|outlook)",
          r"guidance raised", r"record (quarterly )?revenue", r"beats?( analyst)? (estimates|expectations)",
          r"phase 3 .*(met|positive|success)", r"topline .*(met|positive)", r"definitive agreement to (be )?acquire",
          r"to be acquired", r"acquisition of .* for \$", r"awarded .*\$[\d.]+ ?(million|billion)",
          r"contract .*\$[\d.]+ ?(million|billion)", r"strategic partnership with (nvidia|microsoft|amazon|google|meta|openai|apple)"]
TIER_B = [r"phase [12]", r"positive (interim|early|preliminary) data", r"advisory committee", r"adcom",
          r"upgrade", r"initiat(es|ed) coverage", r"contract", r"partnership", r"collaboration",
          r"quarterly results", r"reports (first|second|third|fourth) quarter", r"earnings", r"revenue",
          r"resubmi", r"complete response letter .*resol", r"activist", r"13d", r"stake"]
TIER_C = [r"public offering", r"registered direct", r"private placement", r"at-the-market", r"pricing of",
          r"reverse (stock )?split", r"warrant", r"securities purchase agreement", r"shelf", r"dilut",
          r"investor (alert|notice)", r"class action", r"deadline reminder", r"shareholder rights",
          r"sympathy", r"meme", r"short squeeze"]


def _re_any(pats, s):
    return [p for p in pats if re.search(p, s, re.I)]


# ---------- SEC ----------

def _cik_map():
    def produce():
        j = get("https://www.sec.gov/files/company_tickers.json", ua=SEC_UA, json_out=True)
        if not j:
            return None
        return {v["ticker"].upper(): {"cik": int(v["cik_str"]), "name": v["title"]} for v in j.values()}
    return cache_json("sec_cik_map", 7 * 24 * 3600, produce) or {}


def sec_filings(ticker: str, days: int = 3) -> list[dict]:
    m = _cik_map().get(ticker.upper().replace("-", ""))
    if not m:
        return []
    cik = m["cik"]
    j = get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", ua=SEC_UA, json_out=True, sleep=0.15)
    if not j:
        return []
    rec = j.get("filings", {}).get("recent", {})
    out = []
    cutoff = (today_et() - dt.timedelta(days=days)).isoformat()
    for form, date, acc, doc, items in zip(rec.get("form", []), rec.get("filingDate", []),
                                           rec.get("accessionNumber", []), rec.get("primaryDocument", []),
                                           rec.get("items", [])):
        if date < cutoff:
            continue
        if form not in ("8-K", "8-K/A", "6-K", "425", "S-1", "S-3", "424B5", "424B4", "424B3", "SC 13D", "SC 13G", "10-Q", "10-K"):
            continue
        acc_nodash = acc.replace("-", "")
        out.append({"src": "SEC", "date": date, "form": form, "items": items,
                    "title": f"{form} {items or ''}".strip(),
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"})
    return out


# ---------- Nasdaq ----------

def _mentions(title: str, ticker: str, name: str | None) -> bool:
    t = title.lower()
    if re.search(rf"\b{re.escape(ticker.lower())}\b", t):
        return True
    if name:
        words = [w.lower() for w in re.split(r"[^A-Za-z]+", name) if len(w) > 3 and w.lower() not in
                 {"inc", "corp", "corporation", "ltd", "limited", "holdings", "group", "company", "plc", "technologies", "therapeutics"}]
        return any(w in t for w in words[:2])
    return False


def nasdaq_news(ticker: str, limit: int = 12, name: str | None = None) -> list[dict]:
    j = get("https://api.nasdaq.com/api/news/topic/articlebysymbol",
            params={"q": f"{ticker.upper()}|STOCKS", "offset": 0, "limit": limit, "fallback": "false"},
            ua=CHROME_UA, headers={"Accept": "application/json"}, json_out=True)
    out = []
    try:
        for r in j["data"]["rows"]:
            out.append({"src": "Nasdaq", "date": r.get("created") or r.get("ago") or "", "title": html.unescape(r.get("title", "")),
                        "publisher": r.get("publisher"), "url": "https://www.nasdaq.com" + r.get("url", "") if r.get("url", "").startswith("/") else r.get("url", "")})
    except Exception:
        pass
    return [h for h in out if _mentions(h["title"], ticker, name)]


# ---------- GlobeNewswire ----------

def globenewswire(ticker: str) -> list[dict]:
    txt = get(f"https://www.globenewswire.com/en/search/keyword/{ticker.upper()}", ua="curl/8.5.0")
    out = []
    if not txt:
        return out
    for m in re.finditer(r'<a[^>]+href="(/news-release/[^"]+)"[^>]*data-autid="article-url"[^>]*>(.*?)</a>', txt, re.S):
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        out.append({"src": "GlobeNewswire", "date": "", "title": html.unescape(title),
                    "url": "https://www.globenewswire.com" + m.group(1)})
    # dates sit near each article block
    dates = re.findall(r'data-autid="article-published-date"[^>]*>([^<]+)<', txt)
    for i, d in enumerate(dates[:len(out)]):
        out[i]["date"] = d.strip()
    return out[:10]


# ---------- finviz ----------

def finviz_news(ticker: str) -> list[dict]:
    txt = get(f"https://finviz.com/quote.ashx?t={ticker.upper()}&p=d", ua=CHROME_UA)
    out = []
    if not txt:
        return out
    # rows: <td>Sep-29-26 08:05AM</td> or <td>08:05AM</td> (same day as the previous dated row)
    last_date = ""
    for m in re.finditer(r'<td[^>]*>\s*((?:[A-Z][a-z]{2}-\d\d-\d\d)?)\s*(\d\d:\d\d[AP]M)\s*</td>.*?<a[^>]*class="tab-link-news"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', txt, re.S):
        if m.group(1):
            last_date = m.group(1)
        url = m.group(3)
        if url.startswith("/"):
            url = "https://finviz.com" + url
        out.append({"src": "finviz", "date": f"{last_date} {m.group(2)}".strip(),
                    "title": html.unescape(re.sub(r"<[^>]+>", "", m.group(4))).strip(), "url": url})
    return out[:15]


# ---------- Google News ----------

def google_news(ticker: str, name: str | None = None) -> list[dict]:
    q = f"{ticker} stock" if not name else f'"{name}" OR {ticker} stock'
    txt = get("https://news.google.com/rss/search", params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"}, ua=CHROME_UA)
    out = []
    if not txt:
        return out
    for m in re.finditer(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>", txt, re.S):
        out.append({"src": "GoogleNews", "date": m.group(3), "title": html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))), "url": m.group(2)})
    return out[:10]


def _recent(datestr: str, days: int = 3) -> bool | None:
    """True/False if the date string parses, None if unknown format (kept, flagged)."""
    if not datestr:
        return None
    d = datestr.strip()
    fmts = ["%b %d, %Y", "%b-%d-%y %I:%M%p", "%b-%d-%y", "%a, %d %b %Y %H:%M:%S %Z", "%B %d, %Y", "%Y-%m-%d"]
    for f in fmts:
        try:
            parsed = dt.datetime.strptime(d.split(" GMT")[0] if "GMT" in d else d, f.replace(" %Z", "")).date()
            return (today_et() - parsed).days <= days
        except Exception:
            continue
    return None


MA_CASH = [r"to be acquired .*cash", r"acquired by .* for .*\$[\d.]+ ?(per share|/shr)", r"definitive (merger )?agreement .* all[- ]cash",
           r"take[- ]private", r"in cash", r"to acquire [A-Z][\w ]+ in \$[\d.]+ ?(mln|million|bln|billion) deal",
           r"agreed to be acquired", r"enters? into (definitive )?(merger )?agreement to be acquired"]


def gather(ticker: str, name: str | None = None) -> dict:
    filings = sec_filings(ticker)
    heads_all = nasdaq_news(ticker, name=name) + globenewswire(ticker) + finviz_news(ticker)
    heads = [h for h in heads_all if _recent(h.get("date", "")) is not False]
    if len(heads) < 3:
        heads += [h for h in google_news(ticker, name) if _recent(h.get("date", "")) is not False]
    # heuristic tier from the freshest material (filings + recent headlines)
    corpus = " | ".join([f"{f['form']} {f['items']}" for f in filings] + [h["title"] for h in heads[:8]])
    a, b, c = _re_any(TIER_A, corpus), _re_any(TIER_B, corpus), _re_any(TIER_C, corpus)
    ma = _re_any(MA_CASH, corpus) if re.search(r"acquir|merger|buyout|take[- ]private", corpus, re.I) else []
    items8k = " ".join(f["items"] for f in filings if f["form"].startswith("8-K"))
    if "2.02" in items8k:  # results of operations
        b.append("8-K item 2.02 (earnings)")
    if "1.01" in items8k:
        b.append("8-K item 1.01 (material agreement)")
    if "3.02" in items8k:  # unregistered sale of equity
        c.append("8-K item 3.02 (equity sale)")
    if ma:
        pre, why = "MA-target", ma + ["cash takeover: upside capped at deal price — not an EP"]
    elif c and not a:
        pre, why = "C?", c
    elif a:
        pre, why = "A?", a
    elif b:
        pre, why = "B?", b
    else:
        pre, why = "unknown", []
    return {"ticker": ticker, "filings": filings, "headlines": heads[:15], "pre_tier": pre,
            "pre_tier_hits": why[:5], "pre_tier_note": "heuristic keyword match — confirm by reading the PR/filing"}


if __name__ == "__main__":
    for t in sys.argv[1:] or ["IOVA"]:
        print(json.dumps(gather(t), indent=1)[:4000])
