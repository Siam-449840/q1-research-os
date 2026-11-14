# Changelog

## 1.3.0 (2026-11-14)

Productivity release: the v1.2 gates required many hand-written ledger rows; helpers now write them.

- `rosctl search`: OpenAlex built in (any paper-search source if installed); raw output saved, row logged; failures log nothing.
- `rosctl add-ref <DOI...>`: registry BibTeX via doi.org, stable citekey, immediate registry verification; unresolvable DOIs never added.
- `rosctl fetch-text <key...>`: ACCESS-declared source text (full text from local PDF via pdftotext, else OpenAlex abstract, marked abstract-only).
- `rosctl fetch <URL> --id --license`: download, hash, provenance, run log, read-only; refuses missing licence, overwrites and oversize files.
- `rosctl provenance [--apply]`: candidate results cells for every unprovenanced number; applies only unique matches with >= 3 significant digits and a known producing script; reports CHOOSE/MISSING.
- `rosctl log-ai`, `rosctl next` (blockers grouped by fix command).
- Skills and stage playbooks direct agents to the helpers; per-stage automation table in README and PLAYBOOK.
- Tests: 81 -> 96; mutation testing 32/32 killed (incl. helpers).
- Pilot study fixes: OpenAlex truncated chunked responses (field selection + retry), negative cells lost their
  sign in number matching, classification rule false positive narrowed, `rosctl cite-number` for validated
  manual choices, `provenance` also searches the frozen protocol. Report: docs/PILOT_2026-11.md.
- README rewritten as a complete beginner guide.
- C59 protocol execution ledger: every pre-registered analysis (A# IDs) must be executed (result cell located in a
  logged output) or declared as a deviation; a false "no deviations" claim is blocked [E60,E67,E80,E103]. Found by
  the pilot's independent review, which caught four omitted pre-registered analyses the gates had passed.
- `rosctl run` now records outputs rewritten with identical bytes, so a deterministic re-run after a code edit
  clears the STALE block (pilot finding).
- C60 location-checked provenance: a `file.md:N` row must still find its value on that line, so edits cannot leave
  rows bound to old text (the pilot's second review found 28 such rows). `rosctl provenance --apply` re-points
  shifted rows (same-value rows in reading order; otherwise the nearest unambiguous shift) and never guesses beyond
  that. Line numbers now stay valid across fenced code blocks and HTML comments. Tests 102.

## 1.2.0 (2026-11-14)

Audit against a 136-item catalogue of AI-assisted research errors.

- `core/ERROR_CONTROLS.csv` + `core/CONTROLS.csv`: every error mapped to fail-closed gates and/or
  mandatory human checks; integrity test fails if any mapping, function or test is missing.
- Human checklists enforced by `rosctl approve` (26 items over S1, S2, S8, S9); S8 adds a random spot-check
  of 3 numbers and 3 claims. Approvals recorded with an older checklist must be redone.
- New gates: manuscript language lint, analysis-code hygiene (synthetic fallbacks, silent excepts),
  numeric-coded factors, data schema (units, ranges, date formats, decimal commas, Bengali digits,
  spreadsheet-mangled IDs), personal-data detection, cleaning log, output provenance via
  `ledgers/OUTPUT_MANIFEST.jsonl` (hand-edited and stale outputs blocked), pinned environment,
  `rosctl verify-deps` (anti-slopsquatting), test/evaluation lock after S4, prompt-injection scan,
  protocol method requirements (24 rules), neutral research questions, counter-evidence and grey-literature
  searches with raw outputs, novelty-verdict sections, ACCESS-declared source texts for every citation,
  preprint labelling, reference metadata mismatch, training-set metrics, hypothesis coverage, limitations
  length, AI usage log, figure error-bar type, reviewer model diversity, guide for authors, rebuttal truth.
- Claude Code project permissions template (`.claude/settings.json`) and constitution rules 14-16.
- CI: Python 3.9/3.13 via uv (runner images no longer ship 3.9).
- Tests: 52 -> 81; mutation testing 25/25 killed.

## 1.1.0 (2026-11-14)

Hardening after an adversarial audit in which 7 of 7 gaming attempts passed the v1.0.0 gates.

- `rosctl verify-refs`: every reference resolved at doi.org (Crossref, DataCite, ...), title compared,
  retraction status from OpenAlex, URL-only entries checked; gates read the ledger offline.
- Number provenance now requires a locator to one exact cell (`keycol=keyval:column`, `$.json.path`,
  `line:N`); values must be correct roundings of that cell.
- `rosctl check stats`: statcheck-style recomputation of p-values for t, F, χ², r and z (stdlib;
  max error vs SciPy 8.5e-13 across 2,000 random cases); decision errors flagged.
- `rosctl check splits` + S4 gate: split manifests must show no group in both train and test of a fold.
- Quotes in CLAIM_SUPPORT checked against `literature/text/<citekey>.txt` when available.
- S8 requires four independent reviewer reports and rejects self-scored dimensions.
- `rosctl approve` refused inside AI-agent sessions (environment markers, process ancestry).
- Fixed: CSV writers emitted CRLF, so pasted `rosctl hash` rows created phantom ledger rows.
- Fixed: Crossref JATS markup in registered titles.
- Tests: 28 → 50, including a full S0→S10 end-to-end run with fault injection.

## 1.0.0 (2026-11-14)

Initial release.
