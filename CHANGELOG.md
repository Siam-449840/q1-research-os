# Changelog

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
