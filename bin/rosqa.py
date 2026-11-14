"""Deterministic content checks (stdlib only). Each returns (blockers, warnings) lists of strings.

The bracketed numbers [E12] refer to rows of core/ERROR_CONTROLS.csv (the 136-error control matrix).
Fail-closed: anything ambiguous is a blocker unless explicitly annotated and visible to reviewers.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

Findings = Tuple[List[str], List[str]]
ALLOW_RE = re.compile(r"ros:\s*allow-(random|except|warnings)\s+\S+(\s+\S+){2,}")  # annotation needs a >=3-word reason

# ----------------------------------------------------------------------------- manuscript language

FAKE_CONSENSUS = re.compile(
    r"\b(numerous|many|several|countless|a (large|growing) (number|body) of|most|multiple|various) (previous |prior |recent )?"
    r"(studies|researchers|authors|reports|papers|investigations)\b|\bwidely (accepted|recogni[sz]ed|known|reported)\b|"
    r"\bit is (well[- ]known|well established|generally accepted|universally accepted|widely believed)\b|\b(scientific )?consensus\b",
    re.I)
NOVELTY_CLAIM = re.compile(
    r"\b(the first (study|attempt|time|report|work|investigation)|for the first time|no (previous|prior|other|earlier) "
    r"(study|studies|research|work)|ha(s|ve) never been (studied|investigated|reported|examined|done))\b", re.I)
HEDGED_NOVELTY = re.compile(r"\bto (the best of )?our knowledge\b", re.I)
PROOF_WORDS = re.compile(r"\b(prove[sd]?|proven|proof that)\b", re.I)
NULL_AS_ABSENCE = re.compile(r"\bno (significant )?(effect|difference|relationship|association|impact)\b", re.I)
NONSIG = re.compile(r"not (statistically )?significant|non-?significant|\bp\s*[>≥]|\bn\.s\.", re.I)
SIG_SPIN = re.compile(r"\b(highly significant|marginally significant|approach(ed|ing) significance|trend(ed)? towards? significance|borderline significan)", re.I)
CAUSAL = re.compile(r"\b(causes?|caused|leads? to|led to|drives?|driven by|results? in)\b", re.I)
PLUSMINUS = re.compile(r"±|\+/-")
DISPERSION_LABEL = re.compile(r"\b(SD|SE|SEM|s\.d\.|s\.e\.|standard (deviation|error)|CI|confidence interval|IQR)\b", re.I)
OVERPRECISE = re.compile(r"(?<![\w.])\d+\.\d{5,}(?!\d)")
HYPE = re.compile(r"\b(groundbreaking|revolutionary|paradigm shift|unprecedented|game-changing|breakthrough)\b", re.I)
TORTURED = ["counterfeit consciousness", "profound learning", "profound neural", "irregular woodland", "arbitrary timberland",
            "haphazard woodland", "colossal information", "bosom malignancy", "bosom disease", "flag to commotion",
            "mean square blunder", "straight relapse", "strategic relapse", "choice tree", "versatile organization"]
CITATION = re.compile(r"(?<![\w.])@([A-Za-z][\w:.\-]*\w)")


def sentences(text: str) -> Iterable[Tuple[int, str]]:
    for ln, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for s in re.split(r"(?<=[.!?])\s+", line):
            if s.strip():
                yield ln, s


def check_language(name: str, text: str) -> Findings:
    blockers: List[str] = []
    warnings: List[str] = []
    for ln, s in sentences(text):
        loc = f"{name}:{ln}"
        if FAKE_CONSENSUS.search(s) and len(set(CITATION.findall(s))) < 3:
            blockers.append(f"{loc} consensus claim with < 3 citations: '{s.strip()[:80]}' [E12]")
        if NOVELTY_CLAIM.search(s) and not HEDGED_NOVELTY.search(s):
            blockers.append(f"{loc} unhedged novelty claim (write 'to our knowledge' and rely on S1): '{s.strip()[:80]}' [E17]")
        if PROOF_WORDS.search(s):
            blockers.append(f"{loc} statistics do not 'prove': '{s.strip()[:80]}' [E41]")
        if NULL_AS_ABSENCE.search(s) and NONSIG.search(s):
            blockers.append(f"{loc} non-significance reported as absence of effect: '{s.strip()[:80]}' [E41]")
        if SIG_SPIN.search(s):
            blockers.append(f"{loc} significance spin ('highly/marginally significant'): '{s.strip()[:80]}' [E41,E60]")
        if PLUSMINUS.search(s) and not DISPERSION_LABEL.search(s):
            blockers.append(f"{loc} '±' without saying SD, SE or CI: '{s.strip()[:80]}' [E44]")
        if OVERPRECISE.search(s):
            blockers.append(f"{loc} false precision (>= 5 decimals): '{OVERPRECISE.search(s).group(0)}' [E113]")
        if HYPE.search(s):
            blockers.append(f"{loc} hype word '{HYPE.search(s).group(0)}' [E20]")
        low = s.lower()
        for phrase in TORTURED:
            if phrase in low:
                blockers.append(f"{loc} tortured phrase '{phrase}' (sign of disguised plagiarism) [E71]")
        if CAUSAL.search(s):
            warnings.append(f"{loc} causal wording '{CAUSAL.search(s).group(0)}': confirm the design identifies causation [E48]")
    return blockers, warnings


# ----------------------------------------------------------------------------- analysis code hygiene

SYNTHETIC = re.compile(
    r"np\.random\.(rand|randn|normal|uniform|randint|random|choice|default_rng)\b|\brandom\.(random|uniform|gauss|randint|choice|sample|shuffle)\(|"
    r"\b(make_classification|make_regression|make_blobs|make_moons)\b|\b(dummy|mock|fake|synthetic|simulated)_?(data|df|dataset|values|results|y|x)\b|"
    r"\b(rnorm|runif|rbinom|rpois)\(", re.I)
SILENT_EXCEPT = re.compile(r"^\s*except\b[^:\n]*:\s*(pass|continue|\.\.\.|return( None| 0| \[\]| \{\}| np\.nan)?)\s*(#.*)?$")
BARE_EXCEPT_HEAD = re.compile(r"^\s*except\b[^:\n]*:\s*(#.*)?$")
R_SILENT = re.compile(r"tryCatch\(.*error\s*=\s*function\s*\(\w*\)\s*(NULL|NA|0|invisible\(\))", re.S)
IGNORE_WARNINGS = re.compile(r"warnings\.(filterwarnings|simplefilter)\(\s*['\"]ignore|suppressWarnings\(|options\(warn\s*=\s*-1")


def _annotated(lines: List[str], i: int, kind: str) -> bool:
    for j in (i, i - 1):
        if 0 <= j < len(lines):
            m = ALLOW_RE.search(lines[j])
            if m and m.group(1) == kind:
                return True
    return False


def check_code(files: List[Path], root: Path) -> Findings:
    blockers: List[str] = []
    for f in files:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        rel = f.relative_to(root)
        for i, line in enumerate(lines):
            code = line.split("#", 1)[0] if f.suffix == ".py" else line
            if SYNTHETIC.search(code) and not _annotated(lines, i, "random"):
                blockers.append(f"{rel}:{i + 1} random/synthetic data generator '{SYNTHETIC.search(code).group(0)}'; if legitimate "
                                f"(bootstrap, CV shuffling, simulation study) annotate '# ros: allow-random <reason>' [E31,E100]")
            silent = SILENT_EXCEPT.match(line) or (BARE_EXCEPT_HEAD.match(line) and i + 1 < len(lines)
                                                   and lines[i + 1].strip() in {"pass", "continue", "...", "return None"})
            if silent and not _annotated(lines, i, "except"):
                blockers.append(f"{rel}:{i + 1} exception swallowed silently; handle, log or re-raise [E101]")
            if IGNORE_WARNINGS.search(line) and not _annotated(lines, i, "warnings"):
                blockers.append(f"{rel}:{i + 1} warnings globally suppressed [E101]")
        text = "\n".join(lines)
        if f.suffix.lower() == ".r" and R_SILENT.search(text):
            blockers.append(f"{rel} tryCatch returns NULL/NA on error (silent failure) [E101]")
    return blockers, []


def check_factor_formulas(files: List[Path], root: Path, coded_categoricals: List[str]) -> Findings:
    """Numeric-coded categorical columns used in a model formula must be wrapped as factors. [E115]"""
    blockers: List[str] = []
    for f in files:
        for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "~" not in line:
                continue
            for col in coded_categoricals:
                for m in re.finditer(rf"(?<![\w.]){re.escape(col)}(?![\w.])", line):
                    before = line[:m.start()]
                    if not re.search(r"(C|factor|as\.factor|as_factor)\(\s*$", before):
                        blockers.append(f"{f.relative_to(root)}:{ln} numeric-coded categorical '{col}' used in a formula "
                                        f"without C()/factor(): it would be treated as continuous [E115]")
                        break
    return blockers, []


# ----------------------------------------------------------------------------- data schema, units, formats, PII

SCHEMA_COLUMNS = ["file", "column", "type", "unit", "min", "max", "date_format", "coded_numeric", "notes"]
TYPES = {"continuous", "count", "categorical", "date", "id", "text"}
BENGALI_DIGITS = re.compile(r"[০-৯]")
DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")
EXCEL_DATE = re.compile(r"^\d{1,2}-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$|^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-\d{1,2}$", re.I)
SCI_NOTATION_ID = re.compile(r"^\d+(\.\d+)?e\+\d+$", re.I)
PII_HEADER = re.compile(r"(^|_)(name|full_?name|farmer_?name|phone|mobile|cell|email|e_?mail|nid|national_?id|address|village_?head)($|_)", re.I)
PII_VALUE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?:\+?880|0)1[3-9]\d{8}\b")
MAX_SCAN_ROWS = 200_000


def _num(value: str):
    try:
        return float(value)
    except ValueError:
        return None


def _check_cell(rule: Dict[str, str], value: str) -> str:
    v = value.strip()
    if v == "" or v.upper() in {"NA", "NAN", "NULL"}:
        return ""
    t = rule["type"]
    if BENGALI_DIGITS.search(v):
        return "Bengali digits (convert explicitly) [E111]"
    if t in {"continuous", "count"}:
        if DECIMAL_COMMA.match(v):
            return f"decimal comma '{v}' [E111]"
        x = _num(v.replace(",", "")) if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", v) else _num(v)
        if x is None:
            return f"non-numeric '{v}' in {t} column"
        if rule.get("min") and x < float(rule["min"]):
            return f"{x} below declared min {rule['min']} (unit {rule.get('unit')}) [E33,E110]"
        if rule.get("max") and x > float(rule["max"]):
            return f"{x} above declared max {rule['max']} (unit {rule.get('unit')}) [E33,E110]"
    elif t == "date":
        try:
            datetime.strptime(v, rule["date_format"])
        except ValueError:
            return f"'{v}' does not match date_format {rule['date_format']} [E111]"
    elif t in {"id", "categorical"}:
        if EXCEL_DATE.match(v) or SCI_NOTATION_ID.match(v):
            return f"spreadsheet-mangled value '{v}' [E112]"
    return ""


def check_schema(root: Path) -> Findings:
    blockers: List[str] = []
    warnings: List[str] = []
    path = root / "data/SCHEMA.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8"))) if path.exists() else []
    if not rows:
        return [f"data/SCHEMA.csv missing or empty: declare type, unit, range and date format per analysed column [E33,E110,E111]"], []
    by_file: Dict[str, List[Dict[str, str]]] = {}
    for i, r in enumerate(rows, 2):
        r = {k: (r.get(k) or "").strip() for k in SCHEMA_COLUMNS}
        if r["type"] not in TYPES:
            blockers.append(f"SCHEMA row {i}: type must be one of {sorted(TYPES)}")
            continue
        if r["type"] in {"continuous", "count"} and not r["unit"]:
            blockers.append(f"SCHEMA row {i} ({r['column']}): unit is mandatory for {r['type']} columns [E33,E110]")
        if r["type"] == "date" and not r["date_format"]:
            blockers.append(f"SCHEMA row {i} ({r['column']}): date_format (e.g. %Y-%m-%d) is mandatory [E111]")
        by_file.setdefault(r["file"], []).append(r)
    for rel, rules in by_file.items():
        blockers += _scan_file(root, rel, rules)
    return blockers, warnings


def _scan_file(root: Path, rel: str, rules: List[Dict[str, str]]) -> List[str]:
    f = root / rel
    if not f.is_file() or not rel.startswith("data/"):
        return [f"SCHEMA file '{rel}' not found under data/"]
    out: List[str] = []
    with f.open(newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rules = [r for r in rules if r["column"] in header] + [r for r in rules if r["column"] not in header]
        for r in rules:
            if r["column"] not in header:
                out.append(f"SCHEMA column '{r['column']}' not in {rel}")
        active = [r for r in rules if r["column"] in header]
        bad: Dict[str, int] = {}
        for n, row in enumerate(reader, 2):
            if n > MAX_SCAN_ROWS:
                break
            for r in active:
                msg = _check_cell(r, row.get(r["column"]) or "")
                if msg and bad.get(r["column"], 0) < 3:
                    bad[r["column"]] = bad.get(r["column"], 0) + 1
                    out.append(f"{rel}:{n} column '{r['column']}': {msg}")
    return out


def check_pii(root: Path) -> Findings:
    """Personal data in raw files requires a written ethics/legal basis (data/ETHICS.md). [E37,E124]"""
    hits: List[str] = []
    for f in sorted((root / "data/raw").rglob("*.csv")):
        with f.open(newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh)
            header = next(reader, [])
            cols = [h for h in header if PII_HEADER.search(h.strip())]
            if cols:
                hits.append(f"{f.relative_to(root)} columns {cols}")
                continue
            for n, row in enumerate(reader):
                if n > 1000:
                    break
                if any(PII_VALUE.search(c) for c in row):
                    hits.append(f"{f.relative_to(root)} contains e-mail/phone-like values")
                    break
    ethics = root / "data/ETHICS.md"
    if hits and (not ethics.is_file() or len(re.findall(r"\w+", ethics.read_text(encoding="utf-8"))) < 80):
        return [f"personal data detected ({'; '.join(hits[:3])}): write data/ETHICS.md (>= 80 words: consent, approval, "
                f"anonymisation, licence) [E37,E124]"], []
    return [], [f"personal data present, governed by data/ETHICS.md: {h}" for h in hits]


# ----------------------------------------------------------------------------- prompt injection

INJECTION = re.compile(
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts)|disregard (all |the |any )?(previous|prior|above)|"
    r"\byou are (now )?(an? |the )?(ai|assistant|language model|llm|reviewer)\b|\bas an ai\b|"
    r"(give|write|provide) (a |an |this )?(positive|favou?rable|glowing) (review|assessment|evaluation)|"
    r"(do not|don't|never) (mention|highlight|report) (any )?(weakness|limitation|flaw)|system prompt|<\|im_start\|>|\[/?INST\]|"
    r"new instructions?:", re.I)
ZERO_WIDTH = re.compile("[​‌‍⁠﻿‮]")


def scan_injection(text: str) -> List[str]:
    found = [m.group(0) for m in INJECTION.finditer(text)][:3]
    if ZERO_WIDTH.search(text):
        found.append("zero-width/bidi control characters")
    return found


# ----------------------------------------------------------------------------- quotes from participants, rebuttal truthfulness

ATTRIBUTION = re.compile(r"\b(farmer|respondent|participant|interviewee|informant|extension officer|key informant|FGD)\b", re.I)
QUOTED = re.compile(r"[\"“]([^\"”]{20,})[\"”]")


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9%০-৯ঀ-৿]+", text.lower()))


def check_participant_quotes(manuscript: str, sources: List[Path]) -> Findings:
    corpus = _norm(" ".join(p.read_text(encoding="utf-8", errors="replace") for p in sources))
    blockers = []
    for ln, s in sentences(manuscript):
        if ATTRIBUTION.search(s):
            for q in QUOTED.findall(s):
                if _norm(q) not in corpus:
                    blockers.append(f"manuscript:{ln} participant quote not found verbatim in data/raw transcripts: '{q[:60]}' [E122]")
    return blockers, []


def check_rebuttal_changes(response: str, manuscript: str) -> Findings:
    """Every '**Change:**' must quote new text that really exists in the manuscript. [E127]"""
    body = _norm(manuscript)
    blockers = []
    for ln, line in enumerate(response.splitlines(), 1):
        if line.strip().startswith("**Change"):
            quotes = QUOTED.findall(line) or re.findall(r"[\"“]([^\"”]{8,})[\"”]", line)
            if not quotes:
                blockers.append(f"RESPONSE_TO_REVIEWERS:{ln} '**Change:**' must quote the new manuscript text [E127]")
            for q in quotes:
                if _norm(q) not in body:
                    blockers.append(f"RESPONSE_TO_REVIEWERS:{ln} claimed change not found in manuscript: '{q[:60]}' [E127]")
    return blockers, []


# ----------------------------------------------------------------------------- protocol method requirements

PROTOCOL_RULES = [
    (r"anova|analysis of variance", r"type (i|ii|iii|1|2|3)\b|sum of squares", "ANOVA needs the sum-of-squares type (I/II/III) [E116]"),
    (r"anova|t-test|t test|linear model|regression|mixed model", r"assumption|normality|homoscedastic|homogeneity|levene|shapiro|residual",
     "parametric tests need planned assumption checks [E40]"),
    (r"post[- ]hoc|tukey|\blsd\b|dmrt|duncan|scheff|bonferroni", r"family-?wise|error rate|multiple comparison|adjust|correction",
     "post-hoc tests need a stated error-rate control and justification [E42,E43]"),
    (r"mixed[- ]effects?|mixed model|random effects?|hierarchical|multilevel|lme4|glmm", r"random (effect|intercept|slope)s?",
     "mixed models must state which effects are random [E117]"),
    (r"mixed[- ]effects?|mixed model|random effects?|hierarchical|multilevel", r"fixed effects?", "mixed models must state the fixed effects [E117]"),
    (r"log[- ]?transform|log\(|square[- ]root transform|arcsine|box-?cox", r"back[- ]?transform", "transformations need a back-transformation plan [E118]"),
    (r"log[- ]?transform|log\(", r"\bzero", "log transformation must say how zeros are handled [E118]"),
    (r"spatial|time series|temporal|repeated measures?|panel|longitudinal|multi-?year|multi-?site", r"autocorrelation|dependence|cluster|random effect|block|spatial cross-validation|leave-",
     "spatial/temporal data need an explicit dependence strategy [E119,E35]"),
    (r"rcbd|randomi[sz]ed complete block|split[- ]plot|factorial|replicat|latin square", r"experimental unit", "define the experimental unit (pseudoreplication) [E24,E25]"),
    (r"factorial|two-way|interaction|×", r"interaction", "factorial designs need an interaction-analysis plan [E45]"),
    (r"sample size|power analysis|statistical power", r"effect size", "power/sample size needs the assumed effect size [E26]"),
    (r"sample size|power analysis|statistical power", r"source|based on|derived from|pilot|literature", "power/sample size assumptions need a source [E26]"),
    (r"likert", r"ordinal|interval assumption", "Likert data: state ordinal treatment or justify interval assumption [E121]"),
    (r"survey|questionnaire|interview|respondent|farmer|household", r"ethic|consent|irb|review board|approval", "human-participant data need an ethics/consent plan [E124,E37]"),
    (r"causal|effect of|impact of|treatment effect|attributable", r"identification|confound|randomi[sz]|instrument|difference-in-differences|control group|counterfactual|matching",
     "causal questions need an identification strategy and confounder control [E23,E27]"),
    (r"machine learning|random forest|xgboost|gradient boosting|neural network|deep learning|classifier|svm", r"seed",
     "ML needs fixed random seeds [E54,E57]"),
    (r"machine learning|random forest|xgboost|gradient boosting|neural network|deep learning|classifier|svm", r"repeat|multiple seeds|runs|variance across",
     "ML results need repeated runs / variance across seeds [E54]"),
    (r"machine learning|random forest|xgboost|gradient boosting|neural network|deep learning|classifier|svm", r"nested|validation set|held-out|hold-out|inner fold",
     "hyperparameters must be tuned without touching the test set [E56]"),
    (r"machine learning|random forest|xgboost|gradient boosting|neural network|deep learning|classifier|svm", r"baseline", "ML needs named, equally tuned baselines [E53]"),
    (r"classifi(er|cation)|detection model|disease detection|diagnostic (model|classifier)", r"f1|balanced accuracy|auc|mcc|precision|recall|kappa", "classification needs imbalance-aware metrics, not accuracy alone [E55]"),
    (r"benchmark|public dataset|kaggle|imagenet|plantvillage|well-known dataset", r"contamination|leak|memori", "public benchmarks need a contamination/leakage statement [E109]"),
    (r"genom|sequenc|rna-seq|gwas|snp|annotation", r"genome (build|assembly|version)|reference (genome|assembly)|ensembl release|gff|gtf", "genomic work must pin reference genome/annotation versions [E114]"),
    (r"github|repositor(y|ies)|mining software", r"bot|fork|duplicate", "repository mining must filter bots, forks and duplicates [E123]"),
]


def check_protocol_requirements(protocol: str) -> Findings:
    low = protocol.lower()
    blockers = [f"PROTOCOL: {msg}" for trigger, need, msg in PROTOCOL_RULES if re.search(trigger, low) and not re.search(need, low)]
    return blockers, []


LEADING_RQ = re.compile(r"\bRQ\d+:\*{0,2}\s*(why\b|how (much|far|greatly) (does|do|will|can) .{0,80}\b(improve|increase|reduce|enhance|boost)|to (prove|show|demonstrate) that)", re.I)


def check_neutral_questions(proposal: str) -> Findings:
    blockers = [f"PROPOSAL: research question presupposes its answer: '{m.group(0)[:70]}' - ask neutrally "
                f"('What is the effect of X on Y?') [E83,E84]" for m in LEADING_RQ.finditer(proposal)]
    if re.search(r"\bto (prove|confirm) (that|our)\b", proposal, re.I):
        blockers.append("PROPOSAL: 'to prove/confirm that' signals confirmation bias - state a falsifiable hypothesis [E84,E21]")
    return blockers, []
