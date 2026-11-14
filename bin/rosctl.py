#!/usr/bin/env python3
"""rosctl - the gatekeeper of Q1 Research OS.

Turns research-quality rules into machine-checked gates so an AI agent
(Claude Code, Antigravity, Gemini CLI, Codex, ...) cannot silently skip them.

Stdlib only. Python >= 3.9.  Run `rosctl --help`.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

VERSION = "1.3.0"
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FRAMEWORK_ROOT / "bin"))
import rosauto  # noqa: E402  (sibling stdlib-only modules)
import rosqa  # noqa: E402
import rosrefs  # noqa: E402
import rosstats  # noqa: E402

REVIEW_ROLES = ["editor", "methods", "domain", "reproducibility"]
MIN_LIMITATION_WORDS = 120
OUTPUT_MANIFEST = Path("ledgers/OUTPUT_MANIFEST.jsonl")
OUTPUT_DIRS = ["results", "manuscript/figures", "manuscript/tables"]
METRIC_RE = re.compile(r"\b(R2|R²|r-squared|accuracy|RMSE|MAE|AUC|F1|precision|recall|MAPE|NSE|kappa)\b", re.I)
TRAIN_RE = re.compile(r"\btrain(ing)?\b(?!ed)", re.I)
GUIDE_GLOB = "GUIDE_FOR_AUTHORS.*"
CLAUDE_REQUIRED_DENY = ["Edit(/data/raw/**)", "Edit(/.ros/**)", "Edit(/ledgers/OUTPUT_MANIFEST.jsonl)",
                        "Edit(/ledgers/RUN_LOG.csv)", "Bash(rosctl approve *)", "Bash(rosctl relock-tests *)",
                        "Bash(rosctl ack-injection *)"]
MIN_REVIEW_WORDS = 150
SELF_REVIEWERS = {"", "self", "author", "authors", "writer", "drafting agent"}
AGENT_ENV_MARKERS = ["CLAUDECODE", "AI_AGENT", "CODEX_SANDBOX", "CODEX_MANAGED_BY_NPM", "GEMINI_CLI", "ANTIGRAVITY_AGENT"]
AGENT_PROCESS_NAMES = {"claude", "codex", "gemini", "agy", "antigravity", "cursor-agent", "aider"}
STATE_FILE = Path(".ros/state.json")
STAGES = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]
STAGE_NAMES = {
    "S0": "Proposal intake & lint",
    "S1": "Literature, positioning & novelty",
    "S2": "Protocol & pre-registration freeze",
    "S3": "Data acquisition & provenance",
    "S4": "Analysis pipeline (tested, logged)",
    "S5": "Independent re-computation",
    "S6": "Figures & tables",
    "S7": "Evidence-bound manuscript",
    "S8": "Adversarial Q1 review",
    "S9": "Submission package",
    "S10": "Revision & rebuttal",
}
APPROVAL_STAGES = {"S1", "S2", "S8", "S9"}
RUBRIC_DIMENSIONS = [
    "significance", "novelty", "positioning", "design_validity",
    "external_validity", "statistical_rigor", "baselines", "robustness",
    "reproducibility", "reporting_standards", "clarity", "figures",
    "limitations_honesty", "implications", "journal_fit",
]
MIN_RUBRIC_SCORE = 4
MIN_SEARCH_ROWS = 10
MIN_SEARCH_SOURCES = 3
MIN_CLOSEST_WORK = 10
MIN_VERDICT_WORDS = 150
MAX_ABSTRACT_WORDS = 300
SKIP_INT_MAX = 10  # integers <= this are not provenance-checked (counts like "3 sites")
PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bTBD\b|\bTBA\b|\[VERIFY|\bXXX\b|lorem ipsum|<(?!https?:)[A-Za-z][^<>\n]{1,200}>")
NUMBER_RE = re.compile(r"(?<![\w.@/])(?:(?<=[\s(=:,])[-−])?\d[\d,]*(?:\.\d+)?%?(?![\w/]|\.\d)")
CITE_RE = re.compile(r"(?<![\w.])@([A-Za-z][\w:.\-]*\w)")
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@\w+\s*\{|\Z)", re.S)
REF_STRIP_RE = re.compile(
    r"\b(?:Fig(?:ure)?s?|Tables?|Sections?|Eqs?|Equations?|Appendix|Supplementary|Algorithm|Step|Stage|RQ|H|S)\.?\s*[A-Z]?\d+(?:\.\d+)*[a-z]?",
    re.I,
)

PROPOSAL_SECTIONS = [
    ("metadata", "Metadata", 25),
    ("contribution", "Contribution", 15),
    ("problem", "Problem", 60),
    ("gap", "Gap", 60),
    ("research questions", "Research Questions", 60),
    ("data", "Data", 40),
    ("methods", "Methods", 80),
    ("expected results", "Expected Results", 40),
    ("threats", "Threats", 30),
    ("ethics", "Ethics", 15),
    ("definition of done", "Definition of Done", 20),
    ("constraints", "Constraints", 15),
    ("owner", "Decisions Reserved for the Owner", 10),
]
PROTOCOL_SECTIONS = [
    "research questions", "hypotheses", "data", "variables", "primary analysis",
    "validation", "robustness", "multiple", "stopping", "success criteria", "deviations",
]
MANUSCRIPT_SECTIONS = [
    "abstract", "introduction", "method", "results", "discussion", "limitation",
    "conclusion", "data availability", "code availability", "generative ai",
]
HYPE_WORDS = ["groundbreaking", "revolutionary", "paradigm shift", "first ever", "unprecedented", "game-changing"]


# --------------------------------------------------------------------------- utils

class Report:
    """Collects blockers (fail the gate) and warnings (do not)."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.blockers: List[str] = []
        self.warnings: List[str] = []

    def block(self, msg: str) -> None:
        self.blockers.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.blockers

    def extend(self, other: "Report") -> None:
        self.blockers += [f"[{other.title}] {m}" for m in other.blockers]
        self.warnings += [f"[{other.title}] {m}" for m in other.warnings]

    def print(self) -> None:
        mark = "PASS" if self.ok else "FAIL"
        print(f"== {self.title}: {mark} ({len(self.blockers)} blockers, {len(self.warnings)} warnings)")
        for m in self.blockers:
            print(f"  [BLOCKER] {m}")
        for m in self.warnings:
            print(f"  [warning] {m}")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in csv.DictReader(fh)]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(args: List[str], cwd: Path) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def git_commit(root: Path) -> str:
    head = git(["rev-parse", "--short", "HEAD"], root) or "nogit"
    dirty = git(["status", "--porcelain"], root)
    return head + ("+dirty" if dirty else "")


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def split_sections(text: str, level: int = 2) -> Dict[str, str]:
    """Map lower-cased heading text -> body for headings of exactly `level` #'s."""
    pattern = re.compile(rf"^{'#' * level}\s+(.+?)\s*$", re.M)
    hits = list(pattern.finditer(text))
    out: Dict[str, str] = {}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out[m.group(1).strip().lower()] = text[m.end():end]
    return out


def find_section(sections: Dict[str, str], key: str) -> Optional[str]:
    for heading, body in sections.items():
        if re.search(rf"\b{re.escape(key)}\b", heading):
            return body
    return None


def words(text: str) -> int:
    return len(re.findall(r"\w+", strip_code(text)))


def placeholders(text: str) -> List[str]:
    return sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(strip_code(text))})


def to_float(token: str) -> Optional[float]:
    t = token.replace(",", "").replace("−", "-").rstrip("%")
    try:
        return float(t)
    except ValueError:
        return None


def decimals(token: str) -> int:
    t = token.rstrip("%")
    return len(t.split(".")[1]) if "." in t else 0


# --------------------------------------------------------------------------- state

def load_state(root: Path) -> dict:
    path = root / STATE_FILE
    if not path.exists():
        raise SystemExit(f"error: {path} not found. Run `rosctl init <dir>` or cd into a project.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(root: Path, state: dict) -> None:
    path = root / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def protocol_core(root: Path) -> str:
    """Protocol text above '## Deviations' - the frozen part."""
    text = read_text(root / "protocol/PROTOCOL.md")
    m = re.search(r"^##\s+.*deviation", text, flags=re.I | re.M)
    return text[: m.start()] if m else text


def protocol_hash(root: Path) -> str:
    return hashlib.sha256(protocol_core(root).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- proposal lint

def lint_proposal(path: Path) -> Report:
    rep = Report("proposal")
    text = read_text(path)
    if not text:
        rep.block(f"{path} missing or empty")
        return rep
    sections = split_sections(text)
    for key, label, min_words in PROPOSAL_SECTIONS:
        body = find_section(sections, key)
        if body is None:
            rep.block(f"missing section '## ... {label}'")
        elif words(body) < min_words:
            rep.block(f"section '{label}' has {words(body)} words (< {min_words}); be specific")
    for ph in placeholders(text):
        rep.block(f"placeholder text left: {ph!r}")
    _lint_contribution(sections, rep)
    _lint_hypotheses(sections, rep)
    _lint_data(sections, rep)
    _lint_methods(sections, rep)
    _lint_soft(sections, text, rep)
    return rep


def _lint_contribution(sections: Dict[str, str], rep: Report) -> None:
    body = find_section(sections, "contribution") or ""
    if words(body) > 80:
        rep.warn("contribution statement > 80 words; a Q1 editor must grasp it in one breath")
    meta = find_section(sections, "metadata") or ""
    if "target journal" not in meta.lower():
        rep.block("Metadata must list 'Target journals' (ranked, >= 2)")
    if "domain pack" not in meta.lower():
        rep.block("Metadata must name the 'Domain pack' (e.g. agriculture)")


def _lint_hypotheses(sections: Dict[str, str], rep: Report) -> None:
    body = find_section(sections, "research questions") or ""
    rqs = set(re.findall(r"\bRQ\s?(\d+)\b", body))
    hyps = set(re.findall(r"\bH\s?(\d+)\b", body))
    if not 1 <= len(rqs) <= 4:
        rep.block(f"need 1-4 research questions labelled RQ1.., found {len(rqs)}")
    if not 1 <= len(hyps) <= 8:
        rep.block(f"need 1-8 hypotheses labelled H1.., found {len(hyps)}")
    low = body.lower()
    for field in ("rival", "prediction", "decision rule"):
        n = low.count(field)
        if n < len(hyps):
            rep.block(f"each hypothesis needs a '{field}' line ({n} found for {len(hyps)} hypotheses)")
    if "smallest effect" not in low and "effect size" not in low:
        rep.warn("state the smallest effect size of interest for each hypothesis")


def _lint_data(sections: Dict[str, str], rep: Report) -> None:
    body = find_section(sections, "data") or ""
    if not re.search(r"https?://", body):
        rep.block("Data section needs at least one dataset URL")
    if not re.search(r"licen[cs]e", body, re.I):
        rep.block("Data section must state each dataset's license")
    if not re.search(r"access", body, re.I):
        rep.warn("state access status for each dataset (downloaded / API / request needed)")


def _lint_methods(sections: Dict[str, str], rep: Report) -> None:
    low = (find_section(sections, "methods") or "").lower()
    if "baseline" not in low:
        rep.block("Methods must name baselines (strongest published + simple reference)")
    if not re.search(r"cross-validation|held-out|hold-out|leave-|out-of-sample|external validation|independent test", low):
        rep.block("Methods must define the validation strategy (e.g. leave-location-out, leave-year-out)")
    if not re.search(r"robust|sensitivity|ablation", low):
        rep.block("Methods must plan robustness / sensitivity / ablation analyses")
    if not re.search(r"uncertaint|confidence interval|credible interval|bootstrap", low):
        rep.warn("plan uncertainty quantification (CIs, bootstrap, posterior intervals)")


def _lint_soft(sections: Dict[str, str], text: str, rep: Report) -> None:
    figs = len(re.findall(r"\bFig(?:ure)?\.?\s*\d", find_section(sections, "expected results") or "", re.I))
    if figs < 3:
        rep.warn(f"plan >= 3 figures with their one-line message (found {figs})")
    threats = find_section(sections, "threats") or ""
    if len(re.findall(r"^\s*[-*\d]", threats, re.M)) < 3:
        rep.warn("list >= 3 threats to validity, each with a mitigation")
    low = text.lower()
    for w in HYPE_WORDS:
        if w in low:
            rep.warn(f"hype word '{w}' - Q1 reviewers distrust it; state the evidence instead")


def proposal_score(rep: Report) -> int:
    return max(0, 100 - 15 * len(rep.blockers) - 3 * len(rep.warnings))


# --------------------------------------------------------------------------- manuscript checks

def manuscript_files(root: Path) -> List[Path]:
    d = root / "manuscript"
    return sorted(p for p in d.glob("*.md") if not p.name.startswith("_")) if d.exists() else []


def body_without_references(text: str) -> str:
    m = re.search(r"^#{1,3}\s+references\b.*$", text, flags=re.I | re.M)
    return text[: m.start()] if m else text


def manuscript_numbers(text: str) -> List[Tuple[int, str]]:
    """(line_no, token) for every number that needs provenance."""
    out: List[Tuple[int, str]] = []
    clean = strip_code(body_without_references(text))
    for ln, line in enumerate(clean.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        line = re.sub(r"\[@[^\]]*\]|\[Source:[^\]]*\]|\]\([^)]*\)|https?://\S+", " ", line)
        line = REF_STRIP_RE.sub(" ", line)
        for m in NUMBER_RE.finditer(line):
            tok = m.group(0)
            val = to_float(tok)
            if val is None:
                continue
            is_int = "." not in tok and not tok.endswith("%")
            if is_int and (abs(val) <= SKIP_INT_MAX or 1900 <= val <= 2100):
                continue
            out.append((ln, tok))
    return out


def number_matches(token: str, value: str) -> bool:
    a, b = to_float(token), to_float(value)
    if a is None or b is None:
        return False
    return abs(a - b) <= 1e-12 or token.replace(",", "") == value.replace(",", "")


def resolve_locator(path: Path, locator: str) -> Optional[str]:
    """Return the exact text a locator points to, or None if it does not resolve uniquely.

    Locators: `line:N` (any text file) · `$.key.0.key` (JSON) · `column` (CSV with one data row) ·
    `keycol=keyval:column` (CSV row selected by a key).
    """
    loc = locator.strip()
    m = re.fullmatch(r"line:(\d+)", loc)
    if m:
        lines = read_text(path).splitlines()
        n = int(m.group(1))
        return lines[n - 1] if 1 <= n <= len(lines) else None
    if loc.startswith("$.") and path.suffix.lower() == ".json":
        node = json.loads(read_text(path))
        for part in loc[2:].split("."):
            try:
                node = node[int(part)] if isinstance(node, list) else node[part]
            except (KeyError, IndexError, ValueError, TypeError):
                return None
        return None if isinstance(node, (dict, list)) else str(node)
    if path.suffix.lower() in {".csv", ".tsv"}:
        return _csv_cell(path, loc)
    return None


def _csv_cell(path: Path, loc: str) -> Optional[str]:
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter=delim))
    key, _, col = loc.rpartition(":")
    if key:
        kcol, _, kval = key.partition("=")
        rows = [r for r in rows if (r.get(kcol) or "").strip() == kval.strip()]
    if len(rows) != 1 or col not in rows[0]:
        return None
    return rows[0][col]


def value_matches_cell(value: str, cell: str) -> bool:
    """Manuscript value must be a correct rounding of a number in the located cell/line."""
    target = to_float(value)
    if target is None:
        return False
    tol = 0.5 * 10 ** (-decimals(value)) + 1e-9
    whole = to_float(cell.strip())
    for tok in ([cell.strip()] if whole is not None else NUMBER_RE.findall(cell)):
        x = to_float(tok)
        if x is not None and (abs(x - target) <= tol or (value.endswith("%") and abs(x * 100 - target) <= tol)):
            return True
    return False


def _check_provenance_row(root: Path, i: int, row: Dict[str, str], rep: Report) -> None:
    f = root / row.get("results_file", "")
    if not row.get("results_file") or not f.is_file():
        rep.block(f"NUMBER_PROVENANCE row {i}: results_file '{row.get('results_file')}' not found")
        return
    cell = resolve_locator(f, row.get("locator", ""))
    if cell is None:
        rep.block(f"NUMBER_PROVENANCE row {i}: locator {row.get('locator')!r} does not resolve uniquely in "
                  f"{row['results_file']} (use line:N, $.json.path, column, or keycol=keyval:column)")
    elif not value_matches_cell(row.get("value", ""), cell):
        rep.block(f"NUMBER_PROVENANCE row {i}: value {row.get('value')!r} is not a correct rounding of "
                  f"{cell.strip()!r} at {row['results_file']} [{row.get('locator')}]")


def check_numbers(root: Path) -> Report:
    rep = Report("numbers")
    prov = read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")
    for i, row in enumerate(prov, 2):
        _check_provenance_row(root, i, row, rep)
        if not row.get("script"):
            rep.block(f"NUMBER_PROVENANCE row {i}: 'script' (generator) is empty")
    values = [r.get("value", "") for r in prov]
    files = manuscript_files(root)
    if not files:
        rep.block("no manuscript/*.md files")
    for mf in files:
        for ln, tok in manuscript_numbers(read_text(mf)):
            if not any(number_matches(tok, v) for v in values):
                rep.block(f"{mf.relative_to(root)}:{ln} number {tok} has no row in ledgers/NUMBER_PROVENANCE.csv")
    return rep


def parse_bib(path: Path) -> Dict[str, str]:
    return {m.group(2): m.group(3) for m in BIB_ENTRY_RE.finditer(read_text(path))}


def check_bib(root: Path) -> Report:
    """Every entry needs an identifier AND a current registry verification (rosctl verify-refs)."""
    rep = Report("bibliography")
    bib = parse_bib(root / "refs/refs.bib")
    ledger = {r.get("citekey"): r for r in read_csv(root / rosrefs.LEDGER)}
    for key, body in bib.items():
        f = rosrefs.bib_fields(body)
        if not f.get("doi") and not f.get("url"):
            rep.block(f"refs.bib entry '{key}' has neither doi nor url (cannot be verified)")
            continue
        row = ledger.get(key)
        same_id = row and (rosrefs.norm_doi(f["doi"]) == row.get("doi") if f.get("doi") else f.get("url") == row.get("url"))
        if not same_id:
            rep.block(f"'{key}' not verified against a registry - run `rosctl verify-refs`")
        elif row.get("status") in rosrefs.WEAK_OK_STATUSES:
            rep.warn(f"'{key}' is URL-only (reachable, but title/authors not registry-checked)")
        elif row.get("status") not in rosrefs.OK_STATUSES:
            rep.block(f"'{key}' failed registry verification: {row.get('status')} "
                      f"(registered title: {row.get('registered_title') or '-'}) - fix or remove it")
    return rep


def normalise_quote(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text.lower())  # re-join hyphenated line breaks from PDF text
    return " ".join(re.findall(r"[a-z0-9%.]+", text))


ACCESS_RE = re.compile(r"^ACCESS:\s*(full-text|abstract-only|partial)\b", re.I)


def _check_quotes(root: Path, support: List[Dict[str, str]], cited: List[str], rep: Report) -> None:
    """Fail-closed: every cited source has saved text (first line `ACCESS: full-text|abstract-only|partial`)
    and every recorded quote occurs in it. [E7,E8,E10,E97,E98]"""
    for key in sorted(set(cited)):
        src = root / "literature/text" / f"{key}.txt"
        text = read_text(src)
        m = ACCESS_RE.match(text)
        if not text:
            rep.block(f"'{key}': no saved source text literature/text/{key}.txt - cannot prove it was read [E8,E10]")
        elif not m:
            rep.block(f"literature/text/{key}.txt: first line must be 'ACCESS: full-text', 'ACCESS: abstract-only' or "
                      f"'ACCESS: partial' (truncated input must be declared) [E7,E98]")
        elif m.group(1).lower() != "full-text":
            rep.warn(f"'{key}' cited from {m.group(1).lower()} text only - reviewers must check claims stay within it [E7]")
    for r in support:
        if r.get("citekey") not in cited or not r.get("evidence_quote"):
            continue
        src = root / "literature/text" / f"{r.get('citekey')}.txt"
        if src.is_file() and normalise_quote(r["evidence_quote"]) not in normalise_quote(read_text(src)):
            rep.block(f"CLAIM_SUPPORT {r.get('claim_id')}: quote for '{r.get('citekey')}' not found in "
                      f"literature/text/{r.get('citekey')}.txt - misquotation or wrong source [E4,E10]")


def _check_preprints(root: Path, lines_by_key: Dict[str, List[str]], rep: Report) -> None:
    """Preprints must be labelled as such wherever they are cited. [E14]"""
    for r in read_csv(root / rosrefs.LEDGER):
        if r.get("work_type") == "preprint":
            for line in lines_by_key.get(r.get("citekey", ""), []):
                if "preprint" not in line.lower():
                    rep.block(f"@{r['citekey']} is a preprint (not peer-reviewed) but is cited without saying so: "
                              f"'{line.strip()[:70]}' [E14]")
                    break


def check_citations(root: Path) -> Report:
    rep = check_bib(root)
    rep.title = "citations"
    bib = parse_bib(root / "refs/refs.bib")
    support = read_csv(root / "ledgers/CLAIM_SUPPORT.csv")
    ok_levels = {"supports", "partially_supports", "contrasts"}
    supported = {
        r.get("citekey") for r in support
        if r.get("evidence_location") and r.get("evidence_quote") and r.get("support_level") in ok_levels
    }
    used: Dict[str, str] = {}
    lines_by_key: Dict[str, List[str]] = {}
    for mf in manuscript_files(root):
        text = strip_code(body_without_references(read_text(mf)))
        for ln, line in enumerate(text.splitlines(), 1):
            for key in CITE_RE.findall(line):
                used.setdefault(key, f"{mf.relative_to(root)}:{ln}")
                lines_by_key.setdefault(key, []).append(line)
    for key, loc in sorted(used.items()):
        if key not in bib:
            rep.block(f"{loc} cites @{key} which is not in refs/refs.bib")
        elif key not in supported:
            rep.block(f"{loc} cites @{key} without a CLAIM_SUPPORT row (evidence_location + evidence_quote + support_level)")
    for key in sorted(set(bib) - set(used)):
        rep.warn(f"refs.bib entry '{key}' is never cited")
    cited = [k for k in used if k in bib]
    _check_quotes(root, support, cited, rep)
    _check_preprints(root, lines_by_key, rep)
    return rep


def check_stats(root: Path) -> Report:
    """Recompute p-values from reported test statistics (t, F, chi2, r, z) in the manuscript."""
    rep = Report("stats")
    n = 0
    for mf in manuscript_files(root):
        for res in rosstats.check_text(strip_code(body_without_references(read_text(mf)))):
            n += 1
            if not res.consistent:
                kind = "DECISION ERROR (significance flips)" if res.decision_error else "inconsistent"
                rep.block(f"{mf.relative_to(root)}:{res.line} '{res.text}' is {kind}: recomputed p in "
                          f"[{res.computed_low:.4g}, {res.computed_high:.4g}]")
    if n == 0:
        rep.warn("no APA-style test results found (e.g. 't(23) = 2.45, p = .021'); nothing to recompute")
    return rep


def check_splits(root: Path) -> Report:
    """Leakage audit: within each fold, no group may appear in both train and test."""
    rep = Report("splits")
    d = root / "results/splits"
    files = sorted(d.glob("*.csv")) if d.is_dir() else []
    na = d / "NOT_APPLICABLE.md"
    if not files:
        if na.is_file() and words(read_text(na)) >= 40:
            rep.warn("split audit marked NOT_APPLICABLE; reviewers will judge the justification")
        else:
            rep.block("no split manifest: write results/splits/*.csv (fold,split,group) from the CV code, "
                      "or justify in results/splits/NOT_APPLICABLE.md (>= 40 words)")
        return rep
    for f in files:
        _audit_split_file(root, f, rep)
    return rep


def _audit_split_file(root: Path, f: Path, rep: Report) -> None:
    seen: Dict[Tuple[str, str], set] = {}
    with f.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not {"fold", "split", "group"} <= set(reader.fieldnames or []):
            rep.block(f"{f.relative_to(root)} needs columns fold,split,group")
            return
        for row in reader:
            seen.setdefault((row["fold"], row["split"].strip().lower()), set()).add(row["group"])
    folds = {fold for fold, _ in seen}
    for fold in sorted(folds):
        leaked = seen.get((fold, "train"), set()) & seen.get((fold, "test"), set())
        if leaked:
            rep.block(f"LEAKAGE in {f.relative_to(root)} fold {fold}: groups in both train and test: "
                      f"{', '.join(sorted(leaked)[:5])}")
        if not seen.get((fold, "test")):
            rep.block(f"{f.relative_to(root)} fold {fold} has no test rows")


def check_manuscript_structure(root: Path) -> Report:
    rep = Report("manuscript")
    text = "\n".join(read_text(p) for p in manuscript_files(root))
    low_heads = " | ".join(h.lower() for h in re.findall(r"^#{1,3}\s+(.+)$", text, re.M))
    for sec in MANUSCRIPT_SECTIONS:
        if sec not in low_heads:
            rep.block(f"manuscript is missing a '{sec}' section heading")
    for ph in placeholders(text):
        rep.block(f"placeholder left in manuscript: {ph!r}")
    abstract = find_section(split_sections(text, 2), "abstract") or ""
    if words(abstract) > MAX_ABSTRACT_WORDS:
        rep.warn(f"abstract has {words(abstract)} words; most Q1 journals cap at 150-300")
    for h in sorted(set(re.findall(r"\bH\d+\b", protocol_core(root)))):
        if not re.search(rf"\b{h}\b", text):
            rep.block(f"pre-registered hypothesis {h} is never reported in the manuscript (dropped or renamed) [E60,E80]")
    lim = heading_body(text, "limitation")
    if words(lim) < MIN_LIMITATION_WORDS:
        rep.block(f"Limitations section has {words(lim)} words (< {MIN_LIMITATION_WORDS}); name specific threats and bias direction [E61]")
    return rep


def heading_body(text: str, keyword: str) -> str:
    """Body under the first heading (any level) containing keyword, up to the next heading of the same or higher level."""
    heads = list(re.finditer(r"^(#{1,6})\s+(.+)$", text, re.M))
    for i, m in enumerate(heads):
        if keyword in m.group(2).lower():
            level = len(m.group(1))
            end = next((h.start() for h in heads[i + 1:] if len(h.group(1)) <= level), len(text))
            return text[m.end():end]
    return ""


# --------------------------------------------------------------------------- v1.2 controls (see core/ERROR_CONTROLS.csv)

def _wrap(title: str, findings: Tuple[List[str], List[str]]) -> Report:
    rep = Report(title)
    for b in findings[0]:
        rep.block(b)
    for w in findings[1]:
        rep.warn(w)
    return rep


def manuscript_text(root: Path) -> str:
    return "\n".join(strip_code(body_without_references(read_text(p))) for p in manuscript_files(root))


def check_language(root: Path) -> Report:
    return _wrap("language", rosqa.check_language("manuscript", manuscript_text(root)))


def analysis_code_files(root: Path) -> List[Path]:
    exts = {".py", ".r", ".jl", ".m"}
    return sorted(p for p in (root / "analysis").rglob("*") if p.is_file() and p.suffix.lower() in exts
                  and "tests" not in p.relative_to(root / "analysis").parts)


def check_code(root: Path) -> Report:
    rep = _wrap("code", rosqa.check_code(analysis_code_files(root), root))
    coded = [r["column"] for r in read_csv(root / "data/SCHEMA.csv")
             if r.get("type") == "categorical" and r.get("coded_numeric", "").lower() == "yes"]
    rep.extend(_wrap("factors", rosqa.check_factor_formulas(analysis_code_files(root), root, coded)))
    return rep


def check_schema(root: Path) -> Report:
    rep = _wrap("schema", rosqa.check_schema(root))
    rep.extend(_wrap("privacy", rosqa.check_pii(root)))
    return rep


def check_cleaning_log(root: Path) -> Report:
    """Processed data must come with a cleaning log: what was removed, by which rule and script. [E34]"""
    rep = Report("cleaning")
    processed = [p for p in (root / "data/processed").rglob("*") if p.is_file() and p.name != ".gitkeep"]
    if not processed:
        return rep
    rows = read_csv(root / "ledgers/DATA_CLEANING_LOG.csv")
    if not rows:
        rep.block("data/processed has files but ledgers/DATA_CLEANING_LOG.csv is empty: log every filter, imputation "
                  "and outlier rule with rows_in/rows_out [E34]")
    for i, r in enumerate(rows, 2):
        a, b = to_float(r.get("rows_in", "")), to_float(r.get("rows_out", ""))
        if a is None or b is None or b > a:
            rep.block(f"DATA_CLEANING_LOG row {i}: rows_in/rows_out must be numbers with rows_out <= rows_in [E34]")
        if not r.get("rule") or not (root / r.get("script", "")).is_file():
            rep.block(f"DATA_CLEANING_LOG row {i}: needs the rule and an existing script [E34]")
    return rep


def check_injection(root: Path, state: dict) -> Report:
    """Text from papers/web pages is data, never instructions; flagged files need a human acknowledgement. [E107]"""
    rep = Report("injection")
    acks = state.get("injection_acks", {})
    for f in sorted((root / "literature").rglob("*")):
        if f.is_file() and f.suffix.lower() in {".txt", ".md", ".html", ".json", ".csv"}:
            found = rosqa.scan_injection(read_text(f))
            if found and acks.get(str(f.relative_to(root))) != sha256_file(f):
                rep.block(f"possible prompt injection in {f.relative_to(root)}: {found} - owner must inspect and run "
                          f"`rosctl ack-injection {f.relative_to(root)}` [E107]")
    return rep


def check_participant_quotes(root: Path) -> Report:
    sources = [p for p in (root / "data/raw").rglob("*") if p.is_file() and p.suffix.lower() in {".txt", ".md", ".csv"}]
    return _wrap("participant quotes", rosqa.check_participant_quotes(manuscript_text(root), sources))


def check_ai_log(root: Path) -> Report:
    """AI-assisted steps must be logged (tool, model, version, date, purpose) and declared. [E75,E108]"""
    rep = Report("ai log")
    rows = [r for r in read_csv(root / "ledgers/AI_USAGE_LOG.csv") if r.get("tool") and r.get("model") and r.get("purpose")]
    if not rows:
        rep.block("ledgers/AI_USAGE_LOG.csv needs >= 1 row with tool, model, model_version, date and purpose [E108]")
    declaration = heading_body("\n".join(read_text(p) for p in manuscript_files(root)), "generative ai").lower()
    for tool in sorted({r["tool"] for r in rows}):
        if tool.lower() not in declaration:
            rep.block(f"AI tool '{tool}' is in the usage log but not named in the generative-AI declaration [E75]")
    return rep


def output_manifest(root: Path) -> Dict[str, dict]:
    """Latest logged-run record for every output path: {path: {sha, inputs, command, at}}."""
    latest: Dict[str, dict] = {}
    path = root / OUTPUT_MANIFEST
    for line in read_text(path).splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        for p, sha in entry.get("outputs", {}).items():
            latest[p] = {"sha": sha, "inputs": entry.get("inputs", {}), "command": entry.get("command"), "at": entry.get("at")}
    return latest


def tracked_outputs(root: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for d in OUTPUT_DIRS:
        for p in (root / d).rglob("*") if (root / d).is_dir() else []:
            if p.is_file() and p.name != ".gitkeep":
                out[str(p.relative_to(root))] = sha256_file(p)
    return out


def analysis_inputs(root: Path) -> Dict[str, str]:
    return {str(p.relative_to(root)): sha256_file(p) for p in (root / "analysis").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts} if (root / "analysis").is_dir() else {}


def check_outputs(root: Path) -> Report:
    """Every output file must be byte-identical to what a logged run produced, and not stale. [E31,E49,E50,E102,E128]"""
    rep = Report("outputs")
    manifest = output_manifest(root)
    scripts = {r.get("results_file"): r.get("script") for r in read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")}
    scripts.update({r.get("figure_file"): r.get("script") for r in read_csv(root / "ledgers/FIGURE_MANIFEST.csv")})
    current_inputs = analysis_inputs(root)
    for path, sha in sorted(tracked_outputs(root).items()):
        rec = manifest.get(path)
        if rec is None or rec["sha"] != sha:
            rep.block(f"{path} was not produced by a logged `rosctl run` (hand-written, edited or copied) [E31,E49,E50]")
            continue
        script = scripts.get(path)
        if script and script in rec["inputs"] and current_inputs.get(script) != rec["inputs"][script]:
            rep.block(f"{path} is STALE: {script} changed after the run that produced it; re-run [E102,E128]")
    return rep


def check_environment(root: Path) -> Report:
    """Pinned environment and registry-verified dependencies. [E57,E105]"""
    rep = Report("environment")
    locks = [p for p in ("uv.lock", "renv.lock", "poetry.lock", "requirements.txt", "environment.lock.yml") if (root / p).is_file()]
    if not locks:
        rep.block("no environment lock file (uv.lock, renv.lock, poetry.lock or pinned requirements.txt) [E57]")
    req = root / "requirements.txt"
    if req.is_file():
        for line in read_text(req).splitlines():
            spec = line.split("#")[0].strip()
            if spec and "==" not in spec:
                rep.block(f"requirements.txt line '{spec}' is not pinned with '==' [E57]")
    declared = rosrefs.declared_dependencies(root)
    ledger = {(r.get("ecosystem"), r.get("package")): r for r in read_csv(root / rosrefs.DEP_LEDGER)}
    for eco, name in declared:
        row = ledger.get((eco, name))
        if row is None:
            rep.block(f"dependency '{name}' ({eco}) not verified - run `rosctl verify-deps` before installing [E105]")
        elif row.get("status") != "verified":
            rep.block(f"dependency '{name}' failed verification: {row.get('status')} (possible hallucinated or squatted package) [E105]")
    return rep


def test_files(root: Path) -> Dict[str, str]:
    files: Dict[str, str] = {}
    for d in ("analysis/tests", "analysis/eval"):
        for p in (root / d).rglob("*") if (root / d).is_dir() else []:
            if p.is_file() and "__pycache__" not in p.parts and p.name != ".gitkeep":
                files[str(p.relative_to(root))] = sha256_file(p)
    return files


def check_test_lock(root: Path, state: dict) -> Report:
    """After S4 passes, tests and evaluation code are locked; changing them needs the owner. [E99,E51]"""
    rep = Report("test lock")
    lock = state.get("tests_lock")
    if not lock:
        return rep
    now = test_files(root)
    for path, sha in lock.items():
        if now.get(path) != sha:
            rep.block(f"{path} {'deleted' if path not in now else 'modified'} after the S4 test lock - fixing the code, not "
                      f"the test, is required; owner may run `rosctl relock-tests` with a reason [E99]")
    return rep


def check_recompute(root: Path) -> Report:
    rep = Report("recompute")
    rows = read_csv(root / "ledgers/RECOMPUTATION_AUDIT.csv")
    if not rows:
        rep.block("ledgers/RECOMPUTATION_AUDIT.csv has no rows")
    for i, r in enumerate(rows, 2):
        a, b = to_float(r.get("primary_value", "")), to_float(r.get("independent_value", ""))
        if a is None or b is None:
            rep.block(f"row {i}: primary_value/independent_value not numeric")
            continue
        if r.get("primary_method", "").strip().lower() == r.get("independent_method", "").strip().lower():
            rep.block(f"row {i}: independent_method must differ from primary_method")
        atol = to_float(r.get("abs_tolerance", "")) or 1e-6
        rtol = to_float(r.get("rel_tolerance", "")) or 1e-3
        if abs(a - b) > max(atol, rtol * max(abs(a), abs(b))):
            rep.block(f"row {i} ({r.get('stat_id')}): {a} vs {b} exceeds tolerance - STOP and investigate")
    covered = {r.get("hypothesis_id", "").upper() for r in rows}
    for h in sorted(set(re.findall(r"\bH\d+\b", protocol_core(root)))):
        if h not in covered:
            rep.block(f"hypothesis {h} (from PROTOCOL.md) has no re-computed statistic")
    return rep


def check_review(root: Path) -> Report:
    rep = Report("review")
    scores = {r.get("dimension", "").strip().lower(): r for r in read_csv(root / "review/Q1_SCORECARD.csv")}
    for dim in RUBRIC_DIMENSIONS:
        row = scores.get(dim)
        if row is None:
            rep.block(f"Q1_SCORECARD.csv missing dimension '{dim}'")
            continue
        s = to_float(row.get("score", ""))
        if s is None or not 1 <= s <= 5:
            rep.block(f"dimension '{dim}': score must be 1-5")
        elif s < MIN_RUBRIC_SCORE:
            rep.block(f"dimension '{dim}' scored {s:g} (< {MIN_RUBRIC_SCORE}); fix and re-review")
        if not row.get("evidence"):
            rep.block(f"dimension '{dim}': evidence column empty (scores need justification)")
        if row.get("reviewer", "").strip().lower() in SELF_REVIEWERS:
            rep.block(f"dimension '{dim}': reviewer '{row.get('reviewer')}' is not independent")
    for role in REVIEW_ROLES:
        reports = list((root / "review").glob(f"REVIEW_{role}*.md"))
        if not reports or max(words(read_text(p)) for p in reports) < MIN_REVIEW_WORDS:
            rep.block(f"missing review/REVIEW_{role}_vN.md (>= {MIN_REVIEW_WORDS} words) from an independent reviewer")
    issues = read_csv(root / "review/ISSUES.csv")
    if not issues:
        rep.block("review/ISSUES.csv is empty - a real adversarial review always finds issues")
    for r in issues:
        if r.get("severity", "").lower() == "major" and r.get("status", "").lower() not in {"resolved", "justified"}:
            rep.block(f"major issue {r.get('issue_id')} is '{r.get('status')}' (must be resolved or justified)")
        elif r.get("status", "").lower() == "open":
            rep.warn(f"minor issue {r.get('issue_id')} still open")
    return rep


# --------------------------------------------------------------------------- stage checks

def require_file(root: Path, rel: str, rep: Report, min_words: int = 1) -> str:
    text = read_text(root / rel)
    if not text:
        rep.block(f"{rel} missing")
    elif words(text) < min_words:
        rep.block(f"{rel} has {words(text)} words (< {min_words})")
    for ph in placeholders(text):
        rep.block(f"{rel}: placeholder {ph!r}")
    return text


def stage_s0(root: Path, state: dict) -> Report:
    rep = lint_proposal(root / "PROPOSAL.md")
    rep.extend(_wrap("neutral questions", rosqa.check_neutral_questions(read_text(root / "PROPOSAL.md"))))
    rep.extend(check_claude_settings(root))
    return rep


def check_claude_settings(root: Path) -> Report:
    """Claude Code enforces these in-tool; removing them re-opens raw-data edits and self-approval. [E99,E104,E106]"""
    rep = Report("agent permissions")
    path = root / ".claude/settings.json"
    try:
        deny = set(json.loads(read_text(path)).get("permissions", {}).get("deny", []))
    except ValueError:
        deny = set()
    missing = [r for r in CLAUDE_REQUIRED_DENY if r not in deny]
    if missing:
        rep.block(f".claude/settings.json is missing deny rules {missing} (restore from the framework template) [E104,E106]")
    return rep


def stage_s1(root: Path, state: dict) -> Report:
    rep = Report("S1 literature")
    require_file(root, "literature/SEARCH_PROTOCOL.md", rep, 80)
    log = read_csv(root / "ledgers/SEARCH_LOG.csv")
    sources = {r.get("source", "").lower() for r in log if r.get("source")}
    if len(log) < MIN_SEARCH_ROWS or len(sources) < MIN_SEARCH_SOURCES:
        rep.block(f"SEARCH_LOG needs >= {MIN_SEARCH_ROWS} queries over >= {MIN_SEARCH_SOURCES} sources (has {len(log)}/{len(sources)})")
    closest = read_csv(root / "literature/CLOSEST_WORK.csv")
    if len(closest) < MIN_CLOSEST_WORK:
        rep.block(f"CLOSEST_WORK.csv needs >= {MIN_CLOSEST_WORK} rows (has {len(closest)})")
    bib = parse_bib(root / "refs/refs.bib")
    for r in closest:
        if r.get("overlap_with_us") not in {"none", "partial", "direct"}:
            rep.block(f"CLOSEST_WORK '{r.get('citekey')}': overlap_with_us must be none|partial|direct")
        if r.get("citekey") not in bib:
            rep.block(f"CLOSEST_WORK '{r.get('citekey')}' not in refs/refs.bib")
        if r.get("overlap_with_us") == "direct":
            rep.warn(f"DIRECT overlap with {r.get('citekey')} - owner must judge before approving S1")
    verdict = require_file(root, "literature/NOVELTY_VERDICT.md", rep, MIN_VERDICT_WORDS)
    for need in ("contrary evidence", "search limitation"):
        if not heading_body(verdict, need).strip():
            rep.block(f"NOVELTY_VERDICT.md needs a '{need.title()}' section [E17,E18,E86]")
    _check_search_log(root, log, rep)
    rep.extend(check_bib(root))
    rep.extend(check_injection(root, state))
    return rep


def _check_search_log(root: Path, log: List[Dict[str, str]], rep: Report) -> None:
    purposes = " ".join(r.get("purpose", "").lower() for r in log)
    if "counter" not in purposes:
        rep.block("SEARCH_LOG needs >= 1 query with purpose 'counter-evidence' (search against your own hypothesis) [E86]")
    grey_ok = re.search(r"grey|gray|regional|thesis|institutional", purposes)
    if not grey_ok and words(heading_body(read_text(root / "literature/SEARCH_PROTOCOL.md"), "grey")) < 40:
        rep.block("search grey/regional literature (purpose 'grey' or 'regional') or justify its omission under a "
                  "'Grey literature' heading in SEARCH_PROTOCOL.md [E15]")
    for i, r in enumerate(log, 2):
        raw = root / r.get("raw_output", "")
        if not r.get("raw_output") or not raw.is_file() or raw.stat().st_size == 0:
            rep.block(f"SEARCH_LOG row {i}: raw_output file missing - keep the tool's raw output as evidence [E81]")
            continue
        if raw.suffix == ".json":
            try:
                total = json.loads(read_text(raw)).get("total")
            except (ValueError, AttributeError):
                total = None
            if total is not None and str(total) != r.get("hits", "").strip():
                rep.block(f"SEARCH_LOG row {i}: hits {r.get('hits')} != total {total} in {r['raw_output']} [E81]")


def stage_s2(root: Path, state: dict) -> Report:
    rep = Report("S2 protocol")
    text = require_file(root, "protocol/PROTOCOL.md", rep, 300)
    low_heads = " | ".join(h.lower() for h in re.findall(r"^##\s+(.+)$", text, re.M))
    for sec in PROTOCOL_SECTIONS:
        if sec not in low_heads:
            rep.block(f"PROTOCOL.md missing '## ...{sec}...' section")
    core = protocol_core(root)
    hyps = set(re.findall(r"\bH\d+\b", core))
    if not hyps:
        rep.block("PROTOCOL.md defines no hypotheses H1..")
    if core.lower().count("decision rule") < len(hyps):
        rep.block("every hypothesis needs an explicit 'Decision rule'")
    rep.extend(_wrap("method requirements", rosqa.check_protocol_requirements(core)))
    frozen = state.get("protocol_hash")
    if frozen and frozen != protocol_hash(root):
        rep.block("PROTOCOL.md changed after freeze. Revert it; record changes ONLY under '## Deviations'")
    return rep


def stage_s3(root: Path, state: dict) -> Report:
    rep = Report("S3 data")
    require_file(root, "data/DATA_CARD.md", rep, 120)
    rows = read_csv(root / "ledgers/DATA_PROVENANCE.csv")
    if not rows:
        rep.block("ledgers/DATA_PROVENANCE.csv has no rows")
    for r in rows:
        did = r.get("dataset_id", "?")
        path = root / r.get("path", "")
        if not r.get("source_url", "").startswith("http"):
            rep.block(f"{did}: source_url must be an http(s) URL")
        if not r.get("license"):
            rep.block(f"{did}: license is empty")
        if not r.get("path", "").startswith("data/raw/") or not path.exists():
            rep.block(f"{did}: path '{r.get('path')}' must exist under data/raw/")
        elif path.is_file() and r.get("sha256") != sha256_file(path):
            rep.block(f"{did}: sha256 mismatch - raw data was modified (raw data is read-only)")
    rep.extend(check_schema(root))
    rep.extend(check_cleaning_log(root))
    return rep


def stage_s4(root: Path, state: dict) -> Report:
    rep = Report("S4 analysis")
    frozen_at = state.get("protocol_frozen_at", "")
    runs = [r for r in read_csv(root / "ledgers/RUN_LOG.csv") if r.get("timestamp_utc", "") >= frozen_at]
    if not any(r.get("exit_code") == "0" for r in runs):
        rep.block("no successful `rosctl run` after the protocol freeze")
    if not any(r.get("exit_code") == "0" and re.search(r"pytest|unittest|testthat", r.get("command", "")) for r in runs):
        rep.block("no passing test run logged (rosctl run -- python -m pytest analysis/tests)")
    if not list((root / "analysis/tests").glob("test_*")):
        rep.block("analysis/tests/ has no test_* files")
    results = [p for p in (root / "results").rglob("*") if p.is_file() and p.name != ".gitkeep"]
    if not results:
        rep.block("results/ is empty")
    last = runs[-1] if runs else None
    if last and last.get("exit_code") != "0":
        rep.block(f"last logged run FAILED: {last.get('command')} - fix the root cause, never fake output")
    rep.extend(check_splits(root))
    rep.extend(check_code(root))
    rep.extend(check_environment(root))
    rep.extend(check_outputs(root))
    rep.extend(check_test_lock(root, state))
    return rep


def stage_s5(root: Path, state: dict) -> Report:
    return check_recompute(root)


def stage_s6(root: Path, state: dict) -> Report:
    rep = Report("S6 figures")
    manifest = {r.get("figure_file", ""): r for r in read_csv(root / "ledgers/FIGURE_MANIFEST.csv")}
    figs = [p for p in (root / "manuscript/figures").glob("*") if p.suffix.lower() in {".png", ".pdf", ".svg", ".tif", ".tiff", ".jpg", ".eps"}]
    if not figs:
        rep.block("manuscript/figures/ has no figures")
    for p in figs:
        rel = str(p.relative_to(root))
        row = manifest.get(rel)
        if row is None:
            rep.block(f"{rel} not in ledgers/FIGURE_MANIFEST.csv")
            continue
        if not (root / row.get("script", "")).is_file():
            rep.block(f"{rel}: generating script '{row.get('script')}' not found")
        if row.get("colorblind_safe", "").lower() != "yes":
            rep.block(f"{rel}: colorblind_safe must be 'yes'")
        if p.suffix.lower() in {".png", ".tif", ".tiff", ".jpg"} and (to_float(row.get("dpi", "")) or 0) < 300:
            rep.block(f"{rel}: raster figures need dpi >= 300")
        if row.get("error_bars", "").strip().lower() not in {"none", "sd", "se", "ci95", "ci", "iqr", "range", "pi95"}:
            rep.block(f"{rel}: error_bars must be declared (none|SD|SE|CI95|IQR|range|PI95) [E44,E126]")
    return rep


def stage_s7(root: Path, state: dict) -> Report:
    rep = check_manuscript_structure(root)
    rep.title = "S7 manuscript"
    rep.extend(check_numbers(root))
    rep.extend(check_metric_split(root))
    rep.extend(check_citations(root))
    rep.extend(check_stats(root))
    rep.extend(check_language(root))
    rep.extend(check_ai_log(root))
    rep.extend(check_participant_quotes(root))
    return rep


def check_metric_split(root: Path) -> Report:
    """A performance number may not be traced only to training-set results. [E47]"""
    rep = Report("metric split")
    prov = read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")
    for line in manuscript_text(root).splitlines():
        if not METRIC_RE.search(line):
            continue
        for tok in NUMBER_RE.findall(line):
            rows = [r for r in prov if number_matches(tok, r.get("value", ""))]
            if rows and all(TRAIN_RE.search(" ".join([r.get("locator", ""), r.get("results_file", ""), r.get("notes", "")])) for r in rows):
                rep.block(f"performance value {tok} comes from training data ('{line.strip()[:60]}'); report held-out results [E47]")
    return rep


def stage_s8(root: Path, state: dict) -> Report:
    rep = check_review(root)
    rep.extend(check_reviewer_diversity(root))
    return rep


def check_reviewer_diversity(root: Path) -> Report:
    """At least one reviewer must be a human or a model other than the drafting model(s). [E89,E135]"""
    rep = Report("reviewer diversity")
    drafting = {r.get("model", "").strip().lower() for r in read_csv(root / "ledgers/AI_USAGE_LOG.csv")
                if re.search(r"draft|writ", r.get("purpose", ""), re.I)}
    reviewers = []
    for p in sorted((root / "review").glob("REVIEW_*.md")):
        m = re.search(r"^Reviewer:\s*(.+)$", read_text(p), re.M | re.I)
        if not m:
            rep.block(f"{p.relative_to(root)} must state 'Reviewer: <model id or human name>' [E89]")
        else:
            reviewers.append(m.group(1).strip().lower())
    if reviewers and all(r in drafting for r in reviewers):
        rep.block("every reviewer is the same model that drafted the paper; use a human or a different model family [E89,E135]")
    return rep


def stage_s9(root: Path, state: dict) -> Report:
    rep = Report("S9 submission")
    require_file(root, "submission/COVER_LETTER.md", rep, 150)
    checklist = require_file(root, "submission/SUBMISSION_CHECKLIST.md", rep, 20)
    if re.search(r"^\s*[-*]\s*\[ \]", checklist, re.M):
        rep.block("SUBMISSION_CHECKLIST.md has unchecked '- [ ]' items")
    journals = read_csv(root / "submission/JOURNAL_CHECK.csv")
    if not any(r.get("owner_verified", "").lower() == "yes" and r.get("quartile_source") and r.get("checked_date") for r in journals):
        rep.block("JOURNAL_CHECK.csv needs a row with quartile_source, checked_date and owner_verified=yes")
    guides = [g for g in (root / "submission").glob(GUIDE_GLOB) if g.stat().st_size > 1000]
    if not guides:
        rep.block("download the journal's current guide for authors to submission/GUIDE_FOR_AUTHORS.(pdf|html|txt) - "
                  "never rely on remembered guidelines [E72]")
    return rep


def stage_s10(root: Path, state: dict) -> Report:
    rep = Report("S10 rebuttal")
    text = require_file(root, "review/RESPONSE_TO_REVIEWERS.md", rep, 50)
    comments = len(re.findall(r"^\*\*Comment", text, re.M))
    responses = len(re.findall(r"^\*\*Response", text, re.M))
    if comments == 0 or responses < comments:
        rep.block(f"every '**Comment' needs a '**Response' ({responses}/{comments})")
    rep.extend(_wrap("rebuttal truth", rosqa.check_rebuttal_changes(text, "\n".join(read_text(p) for p in manuscript_files(root)))))
    return rep


STAGE_CHECKS: Dict[str, Callable[[Path, dict], Report]] = {
    "S0": stage_s0, "S1": stage_s1, "S2": stage_s2, "S3": stage_s3, "S4": stage_s4,
    "S5": stage_s5, "S6": stage_s6, "S7": stage_s7, "S8": stage_s8, "S9": stage_s9, "S10": stage_s10,
}


def run_stage_checks(root: Path, state: dict, upto: str) -> Report:
    """Cumulative: gate N re-checks S0..N so later edits cannot break earlier guarantees."""
    total = Report(f"gate {upto}")
    for st in STAGES[: STAGES.index(upto) + 1]:
        total.extend(STAGE_CHECKS[st](root, state))
        if st in APPROVAL_STAGES and st != upto and st not in state.get("approvals", {}):
            total.block(f"{st} needs owner approval: owner runs `rosctl approve {st}` in a real terminal")
        elif st in state.get("approvals", {}):
            missing = [c for c in human_controls(root, st) if c not in state["approvals"][st].get("checklist", [])]
            if missing:
                total.block(f"{st} approval predates the current human checklist (missing {missing}); owner must re-run "
                            f"`rosctl approve {st}`")
    return total


def load_controls(root: Path) -> List[Dict[str, str]]:
    for base in (root / ".ros/core", FRAMEWORK_ROOT / "core"):
        rows = read_csv(base / "CONTROLS.csv")
        if rows:
            return rows
    return []


def human_controls(root: Path, stage: str) -> List[str]:
    return [r["control_id"] for r in load_controls(root) if r.get("kind") == "human" and r.get("stage") == stage]


def spot_check_sample(root: Path, k: int = 3) -> List[str]:
    """Random sample of number and claim provenance rows the owner must check by hand. [E133]"""
    import random
    rng = random.SystemRandom()
    nums = read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")
    claims = read_csv(root / "ledgers/CLAIM_SUPPORT.csv")
    picks = [f"number {r.get('value')} at {r.get('manuscript_location')} <- {r.get('results_file')} [{r.get('locator')}]"
             for r in rng.sample(nums, min(k, len(nums)))]
    picks += [f"claim '{r.get('claim_text', '')[:60]}' <- @{r.get('citekey')} {r.get('evidence_location')}: "
              f"\"{r.get('evidence_quote', '')[:80]}\"" for r in rng.sample(claims, min(k, len(claims)))]
    return picks


# --------------------------------------------------------------------------- commands

def find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / STATE_FILE).exists():
            return p
    raise SystemExit("error: not inside a Q1 Research OS project (no .ros/state.json). Use `rosctl init <dir>`.")


def current_stage(state: dict) -> str:
    for st in STAGES:
        if st not in state.get("passed", {}):
            return st
    return "DONE"


def init_collisions(target: Path) -> List[str]:
    """Files that `init` would overwrite - init must never destroy existing work."""
    dests = [Path(n) for n in ("AGENTS.md", "CLAUDE.md", "GEMINI.md")]
    tpl = FRAMEWORK_ROOT / "templates/project"
    dests += [p.relative_to(tpl) for p in tpl.rglob("*") if p.is_file()]
    skills = FRAMEWORK_ROOT / "skills"
    for d in (".claude/skills", ".agents/skills", ".agent/skills"):
        dests += [Path(d) / p.relative_to(skills) for p in skills.rglob("*") if p.is_file()]
    return [str(d) for d in dests if (target / d).exists()]


def copy_extra_skills(source: str, dest: Path) -> None:
    """Copy third-party skill folders (each with SKILL.md); framework skills win on name clashes."""
    if not source:
        return
    src = Path(source).expanduser()
    if not src.is_dir():
        print(f"warning: extra skills dir {src} not found; skipped")
        return
    for skill in sorted(p for p in src.iterdir() if (p / "SKILL.md").is_file()):
        if (dest / skill.name).exists():
            continue
        shutil.copytree(skill, dest / skill.name, symlinks=False)


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.dir).resolve()
    domain_src = FRAMEWORK_ROOT / "domains" / args.domain
    if not domain_src.is_dir():
        avail = ", ".join(sorted(p.name for p in (FRAMEWORK_ROOT / "domains").iterdir() if p.is_dir()))
        print(f"error: unknown domain '{args.domain}'. Available: {avail}")
        return 2
    if (target / STATE_FILE).exists():
        print(f"error: {target} is already a project")
        return 2
    clashes = init_collisions(target)
    if clashes:
        print("error: refusing to overwrite existing files (move or rename them first):")
        for c in clashes[:20]:
            print(f"  {c}")
        return 2
    shutil.copytree(FRAMEWORK_ROOT / "templates/project", target, dirs_exist_ok=True)
    constitution = read_text(FRAMEWORK_ROOT / "core/CONSTITUTION.md")
    for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        (target / name).write_text(constitution, encoding="utf-8")
    shutil.copytree(domain_src, target / ".ros/domain", dirs_exist_ok=True)
    shutil.copytree(FRAMEWORK_ROOT / "core", target / ".ros/core", dirs_exist_ok=True)
    for skills_dir in (".claude/skills", ".agents/skills", ".agent/skills"):
        shutil.copytree(FRAMEWORK_ROOT / "skills", target / skills_dir, dirs_exist_ok=True)
        copy_extra_skills(args.extra_skills, target / skills_dir)
    save_state(target, {"version": 1, "framework_version": VERSION, "domain": args.domain,
                        "created": now_utc(), "passed": {}, "approvals": {}})
    if not git(["rev-parse", "--git-dir"], target):
        git(["init", "-q"], target)
    print(f"Created project at {target} (domain: {args.domain}).")
    print("Next: write PROPOSAL.md (see docs/PROPOSAL_GUIDE.md), then `rosctl lint-proposal`.")
    return 0


def cmd_lint_proposal(args: argparse.Namespace) -> int:
    rep = lint_proposal(Path(args.file))
    rep.print()
    print(f"Proposal readiness score: {proposal_score(rep)}/100 (pass = no blockers)")
    return 0 if rep.ok else 1


def cmd_status(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    state = load_state(root)
    print(f"Project: {root}  domain={state.get('domain')}  framework={state.get('framework_version')}")
    for st in STAGES:
        mark = "PASS" if st in state.get("passed", {}) else "...."
        appr = ""
        if st in APPROVAL_STAGES:
            appr = "  [approved]" if st in state.get("approvals", {}) else "  [needs owner approval]"
        print(f"  {mark}  {st:<4} {STAGE_NAMES[st]}{appr}")
    print(f"Current stage: {current_stage(state)}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    state = load_state(root)
    stage = (args.stage or current_stage(state)).upper()
    if stage not in STAGES:
        print(f"error: stage must be one of {', '.join(STAGES)}")
        return 2
    rep = run_stage_checks(root, state, stage)
    if rep.ok and stage in APPROVAL_STAGES and stage not in state.get("approvals", {}):
        rep.block(f"checks pass; waiting for owner: `rosctl approve {stage}` (must be typed by a human)")
    rep.print()
    if rep.ok:
        state.setdefault("passed", {})[stage] = {"at": now_utc(), "commit": git_commit(root)}
        if stage == "S4" and not state.get("tests_lock"):
            state["tests_lock"] = test_files(root)
            print(f"Locked {len(state['tests_lock'])} test/evaluation files (changes now need the owner).")
        save_state(root, state)
        print(f"{stage} PASSED. Next stage: {current_stage(state)}")
        return 0
    for later in STAGES[STAGES.index(stage):]:  # a regression invalidates every later pass too
        state.get("passed", {}).pop(later, None)
    save_state(root, state)
    return 1


def cmd_approve(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    state = load_state(root)
    stage = args.stage.upper()
    if stage not in APPROVAL_STAGES:
        print(f"error: only {sorted(APPROVAL_STAGES)} need approval")
        return 2
    refusal = approval_refusal(os.environ, process_ancestry(), sys.stdin.isatty())
    if refusal:
        print(f"REFUSED: {refusal}")
        print("AI agents: STOP here, summarise the evidence, and ask the owner to run this command.")
        return 3
    rep = run_stage_checks(root, state, stage)
    rep.print()
    if not rep.ok:
        print("Cannot approve: stage checks fail.")
        return 1
    checklist = confirm_checklist(root, stage)
    if checklist is None:
        print("Not approved: every checklist item must be confirmed.")
        return 1
    spots = spot_check_sample(root) if stage == "S8" else []
    for item in spots:
        print(f"  SPOT-CHECK: {item}")
        if input("    Open the source yourself. Type 'checked' if it is correct: ").strip().lower() != "checked":
            print("Not approved: spot-check failed or skipped. Fix the item and re-run.")
            return 1
    phrase = f"I APPROVE {stage}"
    if input(f"You are the accountable researcher. Type exactly '{phrase}': ").strip() != phrase:
        print("Not approved.")
        return 1
    record_approval(root, state, stage, args.note or "", checklist, spots)
    print(f"{stage} approved. Now run `rosctl gate {stage}`.")
    return 0


def process_ancestry(limit: int = 15) -> List[str]:
    """Executable basenames of this process's ancestors (best effort; empty if `ps` is unavailable)."""
    names, pid = [], os.getppid()
    for _ in range(limit):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            break
        if not out:
            break
        ppid, _, comm = out.partition(" ")
        names.append(Path(comm.strip()).name)
        if not ppid.strip().isdigit() or int(ppid) <= 1:
            break
        pid = int(ppid)
    return names


def approval_refusal(env: Dict[str, str], ancestry: List[str], is_tty: bool) -> str:
    """Why an approval must be refused, or '' if it may proceed. Defence in depth, not a proof of humanity."""
    if not is_tty or env.get("CI"):
        return "approvals must be typed by the human owner in an interactive terminal."
    marker = next((m for m in AGENT_ENV_MARKERS if env.get(m)), "")
    if marker:
        return f"running inside an AI agent session (environment marker {marker})."
    agent = next((a for a in ancestry if a in AGENT_PROCESS_NAMES or a.startswith("language_server")), "")
    if agent:
        return f"launched from an AI agent process ({agent}). Use your own terminal."
    return ""


def confirm_checklist(root: Path, stage: str) -> Optional[List[str]]:
    """Mandatory human-review items for this stage (core/CONTROLS.csv kind=human). Returns confirmed ids or None."""
    rows = [r for r in load_controls(root) if r.get("kind") == "human" and r.get("stage") == stage]
    print(f"Human checklist for {stage} ({len(rows)} items). Answer 'yes' only if you personally verified it.")
    for r in rows:
        if input(f"  [{r['control_id']}] {r['description']} (yes/no): ").strip().lower() != "yes":
            return None
    return [r["control_id"] for r in rows]


def record_approval(root: Path, state: dict, stage: str, note: str,
                    checklist: Optional[List[str]] = None, spots: Optional[List[str]] = None) -> None:
    state.setdefault("approvals", {})[stage] = {
        "at": now_utc(), "by": getpass.getuser(), "commit": git_commit(root), "note": note,
        "ancestry": process_ancestry()[:6], "checklist": checklist or [], "spot_checks": spots or [],
    }
    if stage == "S2":
        state["protocol_hash"] = protocol_hash(root)
        state["protocol_frozen_at"] = now_utc()
        print("Protocol frozen. Future changes go ONLY under '## Deviations'.")
    save_state(root, state)


def cmd_run(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        print("usage: rosctl run -- <command> [args...]")
        return 2
    start = time.time()
    before = tracked_outputs(root)
    try:
        code = subprocess.run(cmd, cwd=root).returncode
    except OSError as exc:
        print(f"error: cannot execute {cmd[0]}: {exc}")
        code = 127
    if code == 0:
        record_outputs(root, cmd, before)
    log = root / "ledgers/RUN_LOG.csv"
    new = not log.exists() or log.stat().st_size == 0
    with log.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["timestamp_utc", "command", "git_commit", "exit_code", "duration_s", "notes"])
        w.writerow([now_utc(), " ".join(cmd), git_commit(root), code, f"{time.time() - start:.1f}", args.note or ""])
    if code != 0:
        print(f"RUN FAILED (exit {code}). Rule: STOP, report the error, never invent results.")
    return code


def record_outputs(root: Path, cmd: List[str], before: Dict[str, str]) -> None:
    """Append the files this run created or changed, with the analysis code they came from. [E31,E49,E102]"""
    after = tracked_outputs(root)
    changed = {p: sha for p, sha in after.items() if before.get(p) != sha}
    if not changed:
        return
    entry = {"at": now_utc(), "command": " ".join(cmd), "commit": git_commit(root), "outputs": changed,
             "inputs": analysis_inputs(root)}
    path = root / OUTPUT_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def _human_guard() -> int:
    refusal = approval_refusal(os.environ, process_ancestry(), sys.stdin.isatty())
    if refusal:
        print(f"REFUSED: {refusal}")
        return 3
    return 0


def cmd_relock_tests(args: argparse.Namespace) -> int:
    """HUMAN ONLY: accept changed tests/evaluation code after reviewing the diff."""
    root = find_root(Path.cwd())
    if _human_guard():
        return 3
    state = load_state(root)
    if len(args.reason.split()) < 5:
        print("error: --reason must explain the change in >= 5 words")
        return 2
    state["tests_lock"] = test_files(root)
    state.setdefault("relocks", []).append({"at": now_utc(), "by": getpass.getuser(), "reason": args.reason})
    save_state(root, state)
    print(f"Relocked {len(state['tests_lock'])} files.")
    return 0


def cmd_ack_injection(args: argparse.Namespace) -> int:
    """HUMAN ONLY: record that a flagged source file was inspected and its text treated as data only."""
    root = find_root(Path.cwd())
    if _human_guard():
        return 3
    f = (Path.cwd() / args.file).resolve()
    state = load_state(root)
    state.setdefault("injection_acks", {})[str(f.relative_to(root))] = sha256_file(f)
    save_state(root, state)
    print(f"Acknowledged {f.relative_to(root)} (re-flagged automatically if the file changes).")
    return 0


def cmd_verify_deps(args: argparse.Namespace) -> int:
    """Network step: check declared packages exist on PyPI/CRAN and are not brand new. [E105]"""
    root = find_root(Path.cwd())
    rows = rosrefs.verify_dependencies(root)
    if not rows:
        print("no declared dependencies found (requirements*.txt, pyproject.toml, DESCRIPTION)")
        return 0
    path = rosrefs.write_dep_ledger(root, rows)
    bad = [r for r in rows if r["status"] != "verified"]
    for r in rows:
        print(f"  {r['status']:<12} {r['ecosystem']:<5} {r['package']:<30} first release {r['first_release'] or '-'}")
    print(f"wrote {path.relative_to(root)}: {len(rows) - len(bad)}/{len(rows)} verified")
    return 1 if bad else 0


NEXT_HINTS = [
    ("[proposal]", "edit PROPOSAL.md (docs/PROPOSAL_GUIDE.md) or ask the agent: 'use the q1-proposal skill'; then rosctl lint-proposal"),
    ("[neutral questions]", "rephrase the research question neutrally in PROPOSAL.md"),
    ("run `rosctl verify-refs`", "rosctl verify-refs"),
    ("failed registry verification", "fix or remove the entry, then rosctl verify-refs (or rosctl add-ref <DOI> for a correct one)"),
    ("no saved source text", "rosctl fetch-text <citekey>   (put a legal PDF at literature/pdfs/<citekey>.pdf for full text)"),
    ("raw_output file missing", "re-run searches with: rosctl search \"<query>\" --source openalex --purpose main"),
    ("counter-evidence", "rosctl search \"<query against your hypothesis>\" --purpose counter-evidence"),
    ("grey/regional", "rosctl search \"<regional/grey query>\" --purpose grey/regional"),
    ("has no row in ledgers/NUMBER_PROVENANCE", "rosctl provenance --apply   (then add the ambiguous ones by hand)"),
    ("not produced by a logged", "regenerate the file: rosctl run -- <script>"),
    ("STALE", "re-run the producing script: rosctl run -- <script>"),
    ("rosctl verify-deps", "rosctl verify-deps"),
    ("AI_USAGE_LOG", "rosctl log-ai --tool <tool> --model <model> --purpose <what it did>"),
    ("DATA_PROVENANCE.csv has no rows", "rosctl fetch <URL> --id D1 --license \"<license from source page>\""),
    ("needs owner approval", "OWNER, in your own terminal: rosctl approve <stage>"),
    ("waiting for owner", "OWNER, in your own terminal: rosctl approve <stage>"),
    ("predates the current human checklist", "OWNER: re-run rosctl approve <stage>"),
]


def cmd_next(args: argparse.Namespace) -> int:
    """Show the current stage's blockers grouped by the command that fixes them. Writes nothing."""
    root = find_root(Path.cwd())
    state = load_state(root)
    stage = current_stage(state)
    if stage == "DONE":
        print("All stages passed.")
        return 0
    rep = run_stage_checks(root, state, stage)
    print(f"Current stage {stage} ({STAGE_NAMES[stage]}): {len(rep.blockers)} blockers")
    groups: Dict[str, List[str]] = {}
    for b in rep.blockers:
        hint = next((h for needle, h in NEXT_HINTS if needle in b), "manual fix (see the blocker text and the stage playbook)")
        groups.setdefault(hint, []).append(b)
    for hint, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n  -> {hint}   [{len(items)}]")
        for b in items[:4]:
            print(f"     - {b[:150]}")
        if len(items) > 4:
            print(f"     ... and {len(items) - 4} more")
    return 0 if rep.ok else 1


def cmd_search(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    try:
        row = rosauto.run_search(root, args.query, args.source, args.purpose, args.year_from, rosrefs.http_fetch)
    except (RuntimeError, ValueError) as exc:
        print(f"SEARCH FAILED: {exc}")
        return 1
    print(f"logged: {row['hits']} hits from {row['source']} -> {row['raw_output']}")
    return 0


def cmd_add_ref(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    rc = 0
    for doi in args.dois:
        try:
            key, row = rosauto.add_reference(root, doi, rosrefs.http_fetch, args.key if len(args.dois) == 1 else "")
        except RuntimeError as exc:
            print(f"  FAILED {doi}: {exc}")
            rc = 1
            continue
        status = row.get("status")
        print(f"  {status:<18} @{key}  {row.get('registered_title', '')[:70]}")
        rc = rc or (0 if status in rosrefs.OK_STATUSES | {"already_present"} else 1)
    return rc


def cmd_fetch_text(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    rc = 0
    for key in args.keys:
        try:
            print(f"  {rosauto.fetch_text(root, key, rosrefs.http_fetch):<14} literature/text/{key}.txt")
        except (RuntimeError, ValueError) as exc:
            print(f"  FAILED {key}: {exc}")
            rc = 1
    return rc


def _fetch_bytes(max_mb: float) -> Callable[[str], bytes]:
    import urllib.request

    def get(url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": rosrefs.USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp:
            length = int(resp.headers.get("Content-Length") or 0)
            if length > max_mb * 1e6:
                raise RuntimeError(f"{length / 1e6:.0f} MB exceeds --max-mb {max_mb}; ask the owner first")
            data = resp.read(int(max_mb * 1e6) + 1)
            if len(data) > max_mb * 1e6:
                raise RuntimeError(f"download exceeds --max-mb {max_mb}; ask the owner first")
            return data
    return get


def cmd_fetch(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    start = time.time()
    try:
        row = rosauto.download_dataset(root, args.url, args.id, args.license, args.name, _fetch_bytes(args.max_mb), sha256_file)
        code = 0
    except Exception as exc:  # noqa: BLE001 - any failure is reported and logged, never hidden
        print(f"FETCH FAILED: {exc}")
        row, code = None, 1
    rosauto.append_row(root / "ledgers/RUN_LOG.csv", ["timestamp_utc", "command", "git_commit", "exit_code", "duration_s", "notes"],
                       {"timestamp_utc": now_utc(), "command": f"rosctl fetch {args.url} --id {args.id}", "git_commit": git_commit(root),
                        "exit_code": str(code), "duration_s": f"{time.time() - start:.1f}", "notes": "data download"})
    if row:
        print(f"saved {row['path']} ({row['size_bytes']} bytes, sha256 {row['sha256'][:12]}...), provenance row added, file set read-only")
    return code


def _producing_script(root: Path, results_file: str) -> str:
    rec = output_manifest(root).get(results_file)
    if not rec:
        return ""
    return next((t for t in (rec.get("command") or "").split() if t.endswith((".py", ".R", ".r", ".jl"))), "")


def significant_digits(token: str) -> int:
    return len(re.sub(r"[^0-9]", "", token.rstrip("%")).lstrip("0"))


def cmd_provenance(args: argparse.Namespace) -> int:
    """Find the exact results cell for every unprovenanced manuscript number; --apply writes unambiguous rows."""
    root = find_root(Path.cwd())
    values = [r.get("value", "") for r in read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")]
    files = [root / p for p in tracked_outputs(root) if p.startswith(("results/", "manuscript/tables/"))]
    if (root / "protocol/PROTOCOL.md").is_file():
        files.append(root / "protocol/PROTOCOL.md")
    applied = ambiguous = missing = 0
    for mf in manuscript_files(root):
        for ln, tok in manuscript_numbers(read_text(mf)):
            if any(number_matches(tok, v) for v in values):
                continue
            cands = rosauto.locator_candidates(root, tok, value_matches_cell, files)
            loc = f"{mf.relative_to(root)}:{ln}"
            script = (_producing_script(root, cands[0][0]) or ("protocol (pre-registered)" if cands[0][0].startswith("protocol/") else "")) if len(cands) == 1 else ""
            if len(cands) == 1 and significant_digits(tok) >= 3 and script and args.apply:
                rosauto.append_row(root / "ledgers/NUMBER_PROVENANCE.csv", rosauto.NUM_HEADER,
                                   {"number_id": f"auto{len(values) + applied + 1}", "value": tok, "manuscript_location": loc,
                                    "results_file": cands[0][0], "locator": cands[0][1], "script": script,
                                    "notes": "rosctl provenance (unique match)"})
                values.append(tok)
                applied += 1
                print(f"  applied  {tok:<10} {loc} <- {cands[0][0]} [{cands[0][1]}]")
            elif not cands:
                missing += 1
                print(f"  MISSING  {tok:<10} {loc}: no results cell rounds to this value (fabricated or mis-typed?)")
            else:
                ambiguous += 1
                why = "too few significant digits" if len(cands) == 1 else f"{len(cands)} candidates"
                print(f"  CHOOSE   {tok:<10} {loc} ({why}): " + "; ".join(f"{f} [{l}]" for f, l in cands[:4]))
    print(f"applied {applied}, need a decision {ambiguous}, no source {missing}")
    return 1 if missing else 0


def cmd_cite_number(args: argparse.Namespace) -> int:
    """Record a provenance row chosen by a person or agent, but only if the locator and rounding check out."""
    root = find_root(Path.cwd())
    f = root / args.results_file
    if not f.is_file():
        print(f"REFUSED: {args.results_file} not found")
        return 1
    cell = resolve_locator(f, args.locator)
    if cell is None or not value_matches_cell(args.value, cell):
        print(f"REFUSED: {args.value!r} is not a correct rounding of {cell!r} at {args.results_file} [{args.locator}]")
        return 1
    script = args.script or _producing_script(root, args.results_file)
    if not script:
        print("REFUSED: --script is required (no logged run produced this file)")
        return 1
    n = len(read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")) + 1
    rosauto.append_row(root / "ledgers/NUMBER_PROVENANCE.csv", rosauto.NUM_HEADER,
                       {"number_id": f"n{n}", "value": args.value, "manuscript_location": args.at, "results_file": args.results_file,
                        "locator": args.locator, "script": script, "notes": "rosctl cite-number (validated)"})
    print(f"recorded {args.value} <- {args.results_file} [{args.locator}]")
    return 0


def cmd_log_ai(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    rosauto.append_row(root / "ledgers/AI_USAGE_LOG.csv", rosauto.AI_HEADER,
                       {"timestamp_utc": now_utc(), "tool": args.tool, "model": args.model, "model_version": args.model_version,
                        "purpose": args.purpose, "prompt_ref": args.prompt_ref, "output_ref": args.output_ref})
    print("AI usage logged.")
    return 0


def cmd_hash(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    w = csv.writer(sys.stdout, lineterminator="\n")
    for p in args.paths:
        path = Path(p).resolve()
        files = [path] if path.is_file() else sorted(q for q in path.rglob("*") if q.is_file())
        for f in files:
            w.writerow([str(f.relative_to(root)), sha256_file(f), f.stat().st_size])
    return 0


CHECKS: Dict[str, Callable[[Path], Report]] = {
    "numbers": check_numbers, "citations": check_citations, "recompute": check_recompute,
    "review": check_review, "manuscript": check_manuscript_structure, "stats": check_stats,
    "splits": check_splits, "refs": check_bib, "language": check_language, "code": check_code,
    "schema": check_schema, "outputs": check_outputs, "environment": check_environment, "ai-log": check_ai_log,
    "cleaning": check_cleaning_log, "quotes": check_participant_quotes, "metric-split": check_metric_split,
    "reviewers": check_reviewer_diversity, "permissions": check_claude_settings,
}


def cmd_check(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    rep = CHECKS[args.what](root)
    rep.print()
    return 0 if rep.ok else 1


def cmd_verify_refs(args: argparse.Namespace) -> int:
    """Network step: resolve every refs.bib entry against registries and write the ledger."""
    root = find_root(Path.cwd())
    entries = parse_bib(root / "refs/refs.bib")
    if not entries:
        print("refs/refs.bib has no entries")
        return 1
    rows = rosrefs.verify_bib(entries)
    path = rosrefs.write_ledger(root, rows)
    bad = [r for r in rows if r["status"] not in rosrefs.OK_STATUSES | rosrefs.WEAK_OK_STATUSES]
    for r in rows:
        print(f"  {r['status']:<22} {r['citekey']:<28} sim={r['title_similarity'] or '-':<6} {r['registered_title'][:60]}")
    print(f"wrote {path.relative_to(root)}: {len(rows) - len(bad)}/{len(rows)} verified")
    return 1 if bad else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"rosctl {VERSION}  python {sys.version.split()[0]}  framework {FRAMEWORK_ROOT}")
    ok = sys.version_info >= (3, 9)
    tools = [
        ("git", True, "https://git-scm.com/downloads"),
        ("uv", True, "brew install uv  (or https://docs.astral.sh/uv/getting-started/installation/)"),
        ("paper-search", False, "uv tool install paper-search-mcp"),
        ("pqa", False, "uv tool install paper-qa"),
        ("academic-refchecker", False, "uv tool install academic-refchecker"),
        ("bibvet", False, "uv tool install git+https://github.com/dipta007/bibvet"),
        ("zotero-mcp", False, "uv tool install zotero-mcp-server"),
    ]
    for name, required, hint in tools:
        found = shutil.which(name)
        tag = "ok" if found else ("MISSING (required)" if required else "missing (optional)")
        print(f"  {name:<20} {tag:<20} {found or hint}")
        ok = ok and (bool(found) or not required)
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rosctl", description="Q1 Research OS gatekeeper")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init", help="create a new research project")
    s.add_argument("dir")
    s.add_argument("--domain", default="_template", help="domain pack (e.g. agriculture)")
    s.add_argument("--extra-skills", default=os.environ.get("ROS_EXTRA_SKILLS", ""),
                   help="folder of extra skills to install (default: $ROS_EXTRA_SKILLS; set by install.sh --with-extras)")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("lint-proposal", help="check PROPOSAL.md is agent-ready")
    s.add_argument("file", nargs="?", default="PROPOSAL.md")
    s.set_defaults(fn=cmd_lint_proposal)
    sub.add_parser("status", help="show stage progress").set_defaults(fn=cmd_status)
    s = sub.add_parser("gate", help="run the gate for a stage (default: current)")
    s.add_argument("stage", nargs="?")
    s.set_defaults(fn=cmd_gate)
    s = sub.add_parser("approve", help="HUMAN ONLY: approve S1/S2/S8/S9")
    s.add_argument("stage")
    s.add_argument("--note", default="")
    s.set_defaults(fn=cmd_approve)
    s = sub.add_parser("run", help="run and log a command: rosctl run -- python analysis/01.py")
    s.add_argument("--note", default="")
    s.add_argument("command", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("hash", help="print path,sha256,size rows for DATA_PROVENANCE")
    s.add_argument("paths", nargs="+")
    s.set_defaults(fn=cmd_hash)
    s = sub.add_parser("check", help="run one verifier")
    s.add_argument("what", choices=sorted(CHECKS))
    s.set_defaults(fn=cmd_check)
    sub.add_parser("verify-refs", help="resolve refs.bib DOIs/URLs against registries (network)").set_defaults(fn=cmd_verify_refs)
    sub.add_parser("verify-deps", help="check declared packages exist and are >= 90 days old (network)").set_defaults(fn=cmd_verify_deps)
    sub.add_parser("next", help="current blockers grouped by the command that fixes them").set_defaults(fn=cmd_next)
    s = sub.add_parser("search", help="search literature, save raw output, log it (network)")
    s.add_argument("query")
    s.add_argument("--source", default="openalex", help="openalex (built in) or any paper-search source")
    s.add_argument("--purpose", default="main", help="main | counter-evidence | grey/regional | snowball")
    s.add_argument("--year-from", default="")
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("add-ref", help="add references by DOI: registry BibTeX + citekey + verification (network)")
    s.add_argument("dois", nargs="+")
    s.add_argument("--key", default="")
    s.set_defaults(fn=cmd_add_ref)
    s = sub.add_parser("fetch-text", help="save literature/text/<key>.txt with an honest ACCESS header")
    s.add_argument("keys", nargs="+")
    s.set_defaults(fn=cmd_fetch_text)
    s = sub.add_parser("fetch", help="download a dataset into data/raw/<id>/, hash it, add provenance (network)")
    s.add_argument("url")
    s.add_argument("--id", required=True)
    s.add_argument("--license", required=True)
    s.add_argument("--name", default="")
    s.add_argument("--max-mb", type=float, default=2048)
    s.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("provenance", help="find results cells for unprovenanced manuscript numbers")
    s.add_argument("--apply", action="store_true", help="write rows for unique, >= 3-significant-digit matches")
    s.set_defaults(fn=cmd_provenance)
    s = sub.add_parser("cite-number", help="record a chosen provenance row after validating locator and rounding")
    s.add_argument("value")
    s.add_argument("results_file")
    s.add_argument("locator")
    s.add_argument("--at", required=True, help="manuscript location, e.g. manuscript/manuscript.md:12")
    s.add_argument("--script", default="")
    s.set_defaults(fn=cmd_cite_number)
    s = sub.add_parser("log-ai", help="append an AI usage record")
    s.add_argument("--tool", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--purpose", required=True)
    s.add_argument("--model-version", default="")
    s.add_argument("--prompt-ref", default="")
    s.add_argument("--output-ref", default="")
    s.set_defaults(fn=cmd_log_ai)
    s = sub.add_parser("relock-tests", help="HUMAN ONLY: accept changed tests after review")
    s.add_argument("--reason", required=True)
    s.set_defaults(fn=cmd_relock_tests)
    s = sub.add_parser("ack-injection", help="HUMAN ONLY: acknowledge an inspected source flagged for prompt injection")
    s.add_argument("file")
    s.set_defaults(fn=cmd_ack_injection)
    sub.add_parser("doctor", help="check installed tools").set_defaults(fn=cmd_doctor)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
