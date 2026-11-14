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

VERSION = "1.0.0"
FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent
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


def value_in_file(value: str, path: Path) -> bool:
    """True if `value` (as rounded in the manuscript) appears in the results file."""
    target = to_float(value)
    if target is None:
        return False
    tol = 0.5 * 10 ** (-decimals(value)) + 1e-12
    for tok in NUMBER_RE.findall(read_text(path)):
        x = to_float(tok)
        if x is None:
            continue
        if abs(x - target) <= tol or (value.endswith("%") and abs(x * 100 - target) <= tol):
            return True
    return False


def check_numbers(root: Path) -> Report:
    rep = Report("numbers")
    prov = read_csv(root / "ledgers/NUMBER_PROVENANCE.csv")
    for i, row in enumerate(prov, 2):
        f = root / row.get("results_file", "")
        if not row.get("results_file") or not f.is_file():
            rep.block(f"NUMBER_PROVENANCE row {i}: results_file '{row.get('results_file')}' not found")
        elif not value_in_file(row.get("value", ""), f):
            rep.block(f"NUMBER_PROVENANCE row {i}: value {row.get('value')!r} not found in {row['results_file']}")
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
    rep = Report("bibliography")
    bib = parse_bib(root / "refs/refs.bib")
    for key, body in bib.items():
        if not re.search(r"^\s*(doi|url)\s*=", body, re.I | re.M):
            rep.block(f"refs.bib entry '{key}' has neither doi nor url (cannot be verified)")
    return rep


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
    for mf in manuscript_files(root):
        text = strip_code(body_without_references(read_text(mf)))
        for ln, line in enumerate(text.splitlines(), 1):
            for key in CITE_RE.findall(line):
                used.setdefault(key, f"{mf.relative_to(root)}:{ln}")
    for key, loc in sorted(used.items()):
        if key not in bib:
            rep.block(f"{loc} cites @{key} which is not in refs/refs.bib")
        elif key not in supported:
            rep.block(f"{loc} cites @{key} without a CLAIM_SUPPORT row (evidence_location + evidence_quote + support_level)")
    for key in sorted(set(bib) - set(used)):
        rep.warn(f"refs.bib entry '{key}' is never cited")
    return rep


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
    return lint_proposal(root / "PROPOSAL.md")


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
    require_file(root, "literature/NOVELTY_VERDICT.md", rep, MIN_VERDICT_WORDS)
    rep.extend(check_bib(root))
    return rep


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
    return rep


def stage_s7(root: Path, state: dict) -> Report:
    rep = check_manuscript_structure(root)
    rep.title = "S7 manuscript"
    rep.extend(check_numbers(root))
    rep.extend(check_citations(root))
    return rep


def stage_s8(root: Path, state: dict) -> Report:
    return check_review(root)


def stage_s9(root: Path, state: dict) -> Report:
    rep = Report("S9 submission")
    require_file(root, "submission/COVER_LETTER.md", rep, 150)
    checklist = require_file(root, "submission/SUBMISSION_CHECKLIST.md", rep, 20)
    if re.search(r"^\s*[-*]\s*\[ \]", checklist, re.M):
        rep.block("SUBMISSION_CHECKLIST.md has unchecked '- [ ]' items")
    journals = read_csv(root / "submission/JOURNAL_CHECK.csv")
    if not any(r.get("owner_verified", "").lower() == "yes" and r.get("quartile_source") and r.get("checked_date") for r in journals):
        rep.block("JOURNAL_CHECK.csv needs a row with quartile_source, checked_date and owner_verified=yes")
    return rep


def stage_s10(root: Path, state: dict) -> Report:
    rep = Report("S10 rebuttal")
    text = require_file(root, "review/RESPONSE_TO_REVIEWERS.md", rep, 50)
    comments = len(re.findall(r"^\*\*Comment", text, re.M))
    responses = len(re.findall(r"^\*\*Response", text, re.M))
    if comments == 0 or responses < comments:
        rep.block(f"every '**Comment' needs a '**Response' ({responses}/{comments})")
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
    return total


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
        save_state(root, state)
        print(f"{stage} PASSED. Next stage: {current_stage(state)}")
        return 0
    state.get("passed", {}).pop(stage, None)
    save_state(root, state)
    return 1


def cmd_approve(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    state = load_state(root)
    stage = args.stage.upper()
    if stage not in APPROVAL_STAGES:
        print(f"error: only {sorted(APPROVAL_STAGES)} need approval")
        return 2
    if not sys.stdin.isatty() or os.environ.get("CI"):
        print("REFUSED: approvals must be typed by the human owner in an interactive terminal.")
        print("AI agents: STOP here, summarise the evidence, and ask the owner to run this command.")
        return 3
    rep = run_stage_checks(root, state, stage)
    rep.print()
    if not rep.ok:
        print("Cannot approve: stage checks fail.")
        return 1
    phrase = f"I APPROVE {stage}"
    if input(f"You are the accountable researcher. Type exactly '{phrase}': ").strip() != phrase:
        print("Not approved.")
        return 1
    state.setdefault("approvals", {})[stage] = {
        "at": now_utc(), "by": getpass.getuser(), "commit": git_commit(root), "note": args.note or "",
    }
    if stage == "S2":
        state["protocol_hash"] = protocol_hash(root)
        state["protocol_frozen_at"] = now_utc()
        print("Protocol frozen. Future changes go ONLY under '## Deviations'.")
    save_state(root, state)
    print(f"{stage} approved. Now run `rosctl gate {stage}`.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    cmd = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not cmd:
        print("usage: rosctl run -- <command> [args...]")
        return 2
    start = time.time()
    try:
        code = subprocess.run(cmd, cwd=root).returncode
    except OSError as exc:
        print(f"error: cannot execute {cmd[0]}: {exc}")
        code = 127
    log = root / "ledgers/RUN_LOG.csv"
    new = not log.exists() or log.stat().st_size == 0
    with log.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["timestamp_utc", "command", "git_commit", "exit_code", "duration_s", "notes"])
        w.writerow([now_utc(), " ".join(cmd), git_commit(root), code, f"{time.time() - start:.1f}", args.note or ""])
    if code != 0:
        print(f"RUN FAILED (exit {code}). Rule: STOP, report the error, never invent results.")
    return code


def cmd_hash(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    w = csv.writer(sys.stdout)
    for p in args.paths:
        path = Path(p).resolve()
        files = [path] if path.is_file() else sorted(q for q in path.rglob("*") if q.is_file())
        for f in files:
            w.writerow([str(f.relative_to(root)), sha256_file(f), f.stat().st_size])
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = find_root(Path.cwd())
    fn = {"numbers": check_numbers, "citations": check_citations, "recompute": check_recompute,
          "review": check_review, "manuscript": check_manuscript_structure}[args.what]
    rep = fn(root)
    rep.print()
    return 0 if rep.ok else 1


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
    s.add_argument("what", choices=["numbers", "citations", "recompute", "review", "manuscript"])
    s.set_defaults(fn=cmd_check)
    sub.add_parser("doctor", help="check installed tools").set_defaults(fn=cmd_doctor)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
