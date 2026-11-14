"""Reference verification against registries (stdlib only).

For each refs.bib entry:
- DOI  -> resolve via doi.org content negotiation (CSL-JSON; covers Crossref, DataCite, mEDRA ...),
          compare the registered title with the bib title, check the year, and ask OpenAlex
          whether the work is retracted.
- URL only -> check the URL is reachable (weaker; reported as such).
Results are written to ledgers/REFERENCE_VERIFICATION.csv so gates can check offline.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

LEDGER = Path("ledgers/REFERENCE_VERIFICATION.csv")
COLUMNS = ["citekey", "doi", "url", "status", "title_similarity", "registered_title", "registered_year",
           "bib_year", "is_retracted", "source", "checked_at"]
MIN_TITLE_SIMILARITY = 0.85
USER_AGENT = "Q1ResearchOS/1.1 (+https://github.com/Siam-449840/q1-research-os)"
TIMEOUT_S = 20
OK_STATUSES = {"verified"}
WEAK_OK_STATUSES = {"url_reachable"}

Fetch = Callable[[str, Dict[str, str]], Tuple[int, str]]


def http_fetch(url: str, headers: Dict[str, str]) -> Tuple[int, str]:
    """GET with one retry on 429/5xx. Returns (status, body); status 0 on network failure."""
    for attempt in range(2):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(2.0)
                continue
            return exc.code, ""
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 0:
                time.sleep(1.0)
                continue
            return 0, ""
    return 0, ""


def bib_fields(body: str) -> Dict[str, str]:
    """Parse `name = {value}` / `"value"` / bare value fields, honouring nested braces."""
    fields: Dict[str, str] = {}
    for m in re.finditer(r"(\w+)\s*=\s*", body):
        name, i = m.group(1).lower(), m.end()
        if i >= len(body):
            continue
        if body[i] == "{":
            depth, j = 0, i
            while j < len(body):
                depth += {"{": 1, "}": -1}.get(body[j], 0)
                if depth == 0:
                    break
                j += 1
            value = body[i + 1:j]
        elif body[i] == '"':
            j = body.find('"', i + 1)
            value = body[i + 1:j if j > 0 else len(body)]
        else:
            value = re.match(r"[^,\n}]*", body[i:]).group(0)
        fields.setdefault(name, re.sub(r"[{}]", "", value).strip())
    return fields


def norm_doi(doi: str) -> str:
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi.strip(), flags=re.I).lower()


def norm_title(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def title_similarity(a: str, b: str) -> float:
    return round(difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio(), 3)


def _csl_year(meta: dict) -> str:
    for key in ("issued", "published-print", "published-online", "created"):
        parts = (meta.get(key) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            return str(parts[0][0])
    return ""


def _retracted(doi: str, fetch: Fetch) -> str:
    status, body = fetch(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}", {"Accept": "application/json"})
    if status != 200:
        return "unknown"
    try:
        return "yes" if json.loads(body).get("is_retracted") else "no"
    except ValueError:
        return "unknown"


def verify_doi(key: str, fields: Dict[str, str], fetch: Fetch) -> Dict[str, str]:
    doi = norm_doi(fields["doi"])
    row = {"citekey": key, "doi": doi, "url": fields.get("url", ""), "bib_year": fields.get("year", ""),
           "source": "doi.org"}
    status, body = fetch(f"https://doi.org/{urllib.parse.quote(doi, safe='/')}",
                         {"Accept": "application/vnd.citationstyles.csl+json"})
    if status == 404:
        return {**row, "status": "not_found"}
    if status != 200:
        return {**row, "status": f"error_http_{status}"}
    try:
        meta = json.loads(body)
    except ValueError:
        return {**row, "status": "error_bad_response"}
    reg_title = meta.get("title") if isinstance(meta.get("title"), str) else " ".join(meta.get("title") or [])
    reg_title = " ".join(re.sub(r"<[^>]+>", "", reg_title).split())  # Crossref titles may carry JATS markup
    sim = title_similarity(fields.get("title", ""), reg_title) if fields.get("title") else 0.0
    retracted = _retracted(doi, fetch)
    if retracted == "yes" or norm_title(reg_title).startswith("retracted"):
        verdict = "retracted"
    elif sim < MIN_TITLE_SIMILARITY:
        verdict = "title_mismatch"
    else:
        verdict = "verified"
    return {**row, "status": verdict, "title_similarity": f"{sim:.3f}", "registered_title": reg_title,
            "registered_year": _csl_year(meta), "is_retracted": retracted}


def verify_url(key: str, fields: Dict[str, str], fetch: Fetch) -> Dict[str, str]:
    status, _ = fetch(fields["url"], {"Accept": "*/*"})
    return {"citekey": key, "doi": "", "url": fields["url"], "bib_year": fields.get("year", ""),
            "status": "url_reachable" if 200 <= status < 400 else f"url_unreachable_{status}", "source": "http"}


def verify_bib(entries: Dict[str, str], fetch: Fetch = http_fetch, pause_s: float = 0.2) -> List[Dict[str, str]]:
    rows = []
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for key, body in entries.items():
        f = bib_fields(body)
        if f.get("doi"):
            row = verify_doi(key, f, fetch)
        elif f.get("url"):
            row = verify_url(key, f, fetch)
        else:
            row = {"citekey": key, "status": "no_identifier"}
        rows.append({c: row.get(c, "") for c in COLUMNS} | {"checked_at": stamp})
        time.sleep(pause_s)
    return rows


def write_ledger(root: Path, rows: List[Dict[str, str]]) -> Path:
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path
