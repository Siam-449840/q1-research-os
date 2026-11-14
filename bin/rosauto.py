"""Automation helpers that write ledgers correctly so neither the researcher nor the agent hand-crafts rows.

Stdlib only. Network calls go through rosrefs.http_fetch (injectable for tests). Every helper is
conservative: when a result is ambiguous it reports candidates instead of guessing.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import rosrefs

Fetch = Callable[[str, Dict[str, str]], Tuple[int, str]]
SEARCH_HEADER = ["date", "source", "query", "filters", "purpose", "hits", "screened", "included", "raw_output", "notes"]
PROV_HEADER = ["dataset_id", "name", "source_url", "version_or_access_date", "license", "path", "sha256", "size_bytes", "notes"]
NUM_HEADER = ["number_id", "value", "manuscript_location", "results_file", "locator", "script", "notes"]
AI_HEADER = ["timestamp_utc", "tool", "model", "model_version", "purpose", "prompt_ref", "output_ref", "notes"]


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def append_row(path: Path, header: List[str], row: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n", extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in header})


def slug(text: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n] or "query"


# ----------------------------------------------------------------------------- search (E81, E86, E15)

def openalex_search(query: str, fetch: Fetch, year_from: str = "", per_page: int = 25) -> Tuple[int, str]:
    params = {"search": query, "per-page": str(per_page)}
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
    return fetch("https://api.openalex.org/works?" + urllib.parse.urlencode(params), {"Accept": "application/json"})


def run_search(root: Path, query: str, source: str, purpose: str, year_from: str, fetch: Fetch) -> Dict[str, str]:
    """Run one search, keep the raw output, and log it. Returns the SEARCH_LOG row (or raises on failure)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    raw = root / "literature/search_raw" / f"{stamp}_{source}_{slug(query)}.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    if source == "openalex":
        status, body = openalex_search(query, fetch, year_from)
        if status != 200:
            raise RuntimeError(f"OpenAlex returned HTTP {status}; nothing logged")
        data = json.loads(body)
        total = int(data.get("meta", {}).get("count", 0))
        data["total"] = total
        raw.write_text(json.dumps(data, indent=1), encoding="utf-8")
    else:
        exe = shutil.which("paper-search")
        if not exe:
            raise RuntimeError("source needs the paper-search CLI (uv tool install paper-search-mcp); nothing logged")
        cmd = [exe, "search", query, "-n", "25", "-s", source] + (["-y", f"{year_from}-"] if year_from else [])
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        start = out.stdout.find("{")
        if out.returncode != 0 or start < 0:
            raise RuntimeError(f"paper-search failed (exit {out.returncode}); nothing logged")
        data = json.loads(out.stdout[start:])
        total = int(data.get("total", len(data.get("papers", []))))
        raw.write_text(json.dumps(data, indent=1), encoding="utf-8")
    row = {"date": today(), "source": source, "query": query, "filters": f"from {year_from}" if year_from else "",
           "purpose": purpose, "hits": str(total), "screened": "", "included": "",
           "raw_output": str(raw.relative_to(root)), "notes": "logged by rosctl search"}
    append_row(root / "ledgers/SEARCH_LOG.csv", SEARCH_HEADER, row)
    return row


# ----------------------------------------------------------------------------- references (E1-E3, E14, E16)

def make_citekey(bibtex: str, existing: List[str]) -> str:
    f = rosrefs.bib_fields(bibtex.split(",", 1)[1] if "," in bibtex else bibtex)
    family = rosrefs.first_author(f.get("author", "")) or "anon"
    word = next((w for w in re.findall(r"[a-z]{4,}", f.get("title", "").lower())
                 if w not in {"with", "from", "into", "using", "their", "this", "that", "under", "between"}), "work")
    base = f"{family}{f.get('year', 'nd')}{word}"
    key, n = base, 2
    while key in existing:
        key, n = f"{base}{chr(96 + n)}", n + 1
    return key


def add_reference(root: Path, doi: str, fetch: Fetch, key: str = "") -> Tuple[str, Dict[str, str]]:
    """Fetch registry BibTeX for a DOI, append it with a stable citekey, and verify it immediately."""
    doi = rosrefs.norm_doi(doi)
    bib_path = root / "refs/refs.bib"
    text = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
    entries = {m.group(2): m.group(3) for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@\w+\s*\{|\Z)", text, re.S)}
    for k, body in entries.items():
        if rosrefs.norm_doi(rosrefs.bib_fields(body).get("doi", "")) == doi:
            return k, {"status": "already_present"}
    status, bibtex = fetch(f"https://doi.org/{urllib.parse.quote(doi, safe='/')}", {"Accept": "application/x-bibtex"})
    if status != 200 or "@" not in bibtex:
        raise RuntimeError(f"doi.org returned HTTP {status} for {doi}: not added (never type BibTeX by hand)")
    key = key or make_citekey(bibtex, list(entries))
    bibtex = re.sub(r"@(\w+)\s*\{\s*[^,\s]+\s*,", lambda m: f"@{m.group(1)}{{{key},", bibtex.strip(), count=1)
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    with bib_path.open("a", encoding="utf-8") as fh:
        fh.write(("\n" if text and not text.endswith("\n") else "") + bibtex + "\n")
    body = bibtex.split(",", 1)[1]
    row = rosrefs.verify_bib({key: body}, fetch=fetch, pause_s=0)[0]
    upsert_ledger(root, row)
    return key, row


def upsert_ledger(root: Path, row: Dict[str, str]) -> None:
    path = root / rosrefs.LEDGER
    rows = [r for r in (csv.DictReader(path.open(encoding="utf-8")) if path.exists() else []) if r.get("citekey") != row["citekey"]]
    rows.append(row)
    rosrefs.write_ledger(root, [{c: r.get(c, "") for c in rosrefs.COLUMNS} for r in rows])


# ----------------------------------------------------------------------------- source text (E7, E8, E10, E98)

def abstract_from_openalex(work: dict) -> str:
    inv = work.get("abstract_inverted_index") or {}
    pos = sorted((i, w) for w, idx in inv.items() for i in idx)
    return " ".join(w for _, w in pos)


def fetch_text(root: Path, key: str, fetch: Fetch) -> str:
    """Save literature/text/<key>.txt with an honest ACCESS header. Full text only from a local PDF via pdftotext."""
    bib = (root / "refs/refs.bib").read_text(encoding="utf-8")
    m = re.search(rf"@\w+\s*\{{\s*{re.escape(key)}\s*,(.*?)(?=\n@\w+\s*\{{|\Z)", bib, re.S)
    if not m:
        raise RuntimeError(f"'{key}' is not in refs/refs.bib (add it with rosctl add-ref first)")
    out = root / "literature/text" / f"{key}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf = root / "literature/pdfs" / f"{key}.pdf"
    if pdf.is_file() and shutil.which("pdftotext"):
        txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, timeout=300).stdout
        pages = txt.count("\f")
        if len(txt.split()) > 1500:
            out.write_text(f"ACCESS: full-text\nSOURCE: {pdf.relative_to(root)} ({pages} pages, pdftotext)\n\n{txt}", encoding="utf-8")
            return "full-text"
        out.write_text(f"ACCESS: partial\nSOURCE: {pdf.relative_to(root)} (only {len(txt.split())} words extracted)\n\n{txt}", encoding="utf-8")
        return "partial"
    doi = rosrefs.norm_doi(rosrefs.bib_fields(m.group(1)).get("doi", ""))
    if not doi:
        raise RuntimeError(f"'{key}' has no DOI and no local PDF at {pdf.relative_to(root)}")
    status, body = fetch(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}", {"Accept": "application/json"})
    abstract = abstract_from_openalex(json.loads(body)) if status == 200 else ""
    if not abstract:
        raise RuntimeError(f"no abstract available for '{key}' and no local PDF; obtain the paper legally first")
    out.write_text(f"ACCESS: abstract-only\nSOURCE: OpenAlex abstract for doi:{doi} ({today()})\n\n{abstract}\n", encoding="utf-8")
    return "abstract-only"


# ----------------------------------------------------------------------------- data download (E25, E26, E32)

def download_filename(url: str, dataset_id: str) -> str:
    """Readable file name: URL basename, plus an extension inferred from a `format=` query when missing."""
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name or dataset_id
    if not Path(name).suffix:
        fmt = (urllib.parse.parse_qs(parsed.query).get("format") or [""])[0].lower()
        name = f"{dataset_id}_{name}.{fmt or 'dat'}"
    return name


def download_dataset(root: Path, url: str, dataset_id: str, license_: str, name: str, fetch_bytes: Callable[[str], bytes],
                     sha256: Callable[[Path], str]) -> Dict[str, str]:
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("only http(s) sources are accepted")
    if not license_.strip():
        raise RuntimeError("--license is required: read it on the source page; never guess")
    filename = download_filename(url, dataset_id)
    target = root / "data/raw" / dataset_id / filename
    if target.exists():
        raise RuntimeError(f"{target.relative_to(root)} exists; raw data is never overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(fetch_bytes(url))
    row = {"dataset_id": dataset_id, "name": name or filename, "source_url": url,
           "version_or_access_date": f"accessed {today()}", "license": license_,
           "path": str(target.relative_to(root)), "sha256": sha256(target), "size_bytes": str(target.stat().st_size),
           "notes": "downloaded by rosctl fetch"}
    append_row(root / "ledgers/DATA_PROVENANCE.csv", PROV_HEADER, row)
    target.chmod(0o444)
    return row


# ----------------------------------------------------------------------------- number provenance (E38, E39, E65)

def locator_candidates(root: Path, value: str, matches: Callable[[str, str], bool], files: List[Path]) -> List[Tuple[str, str]]:
    """All (results_file, locator) cells whose content correctly rounds to `value`."""
    found: List[Tuple[str, str]] = []
    for f in files:
        rel = str(f.relative_to(root))
        if f.suffix.lower() in {".csv", ".tsv"}:
            found += _csv_candidates(f, rel, value, matches)
        elif f.suffix.lower() == ".json":
            try:
                found += [(rel, loc) for loc, v in _json_leaves(json.loads(f.read_text(encoding="utf-8")), "$") if matches(value, str(v))]
            except ValueError:
                continue
        elif f.suffix.lower() in {".txt", ".log", ".md"}:
            found += [(rel, f"line:{i}") for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
                      if matches(value, line)]
    return found


def _csv_candidates(f: Path, rel: str, value: str, matches) -> List[Tuple[str, str]]:
    delim = "\t" if f.suffix.lower() == ".tsv" else ","
    rows = list(csv.DictReader(f.open(newline="", encoding="utf-8"), delimiter=delim))
    if not rows:
        return []
    key_col = next(iter(rows[0]))
    key_unique = len({r[key_col] for r in rows}) == len(rows)
    out = []
    for r in rows:
        for col, cell in r.items():
            if col != key_col and cell is not None and matches(value, cell):
                if len(rows) == 1:
                    out.append((rel, col))
                elif key_unique:
                    out.append((rel, f"{key_col}={r[key_col]}:{col}"))
    return out


def _json_leaves(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _json_leaves(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _json_leaves(v, f"{path}.{i}")
    else:
        yield path, node
