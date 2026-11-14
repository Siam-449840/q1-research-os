---
name: q1-verify
description: Verification toolkit for Q1 Research OS - number provenance, citation/claim support, independent re-computation audits, reference existence checks and reproducibility re-runs. Use in S5, S7 and S8, whenever a number or citation is added to the manuscript, or when the user asks "check everything" / "is this traceable?".
---

# Verification toolkit

Verification is done by **scripts and second sources**, never by re-reading and agreeing with yourself.

## 1. Built-in checks (rosctl)

```bash
rosctl verify-refs        # NETWORK: resolve every DOI at doi.org, title match, OpenAlex retraction -> ledger
rosctl check refs         # offline: every bib entry verified (not_found / title_mismatch / retracted block)
rosctl check numbers      # every manuscript number ↔ NUMBER_PROVENANCE.csv ↔ exact located cell
rosctl check citations    # every [@key] verified + CLAIM_SUPPORT row; quotes checked against literature/text/
rosctl check stats        # recompute p from t/F/chi2/r/z + df; flags inconsistencies and decision errors
rosctl check splits       # results/splits/*.csv: no group in train and test of the same fold
rosctl check recompute    # RECOMPUTATION_AUDIT within tolerance; every hypothesis covered; methods differ
rosctl check manuscript   # required sections, no placeholders, abstract length
rosctl check review       # scorecard complete, all >= 4, four independent reviewer reports, no open major
```

How `check numbers` decides: it extracts decimals, percentages and integers > 10 (except years and
anything inside `code spans`, `[@...]`, `[Source: ...]`, URLs, or figure/table/section labels) and
requires a matching `value` in `ledgers/NUMBER_PROVENANCE.csv`. Each row's `locator` must resolve to
exactly one place (`keycol=keyval:column` or `column` in CSV, `$.path.0` in JSON, `line:N` in text),
and the manuscript value must be a correct rounding of that exact cell (fraction ↔ percent allowed).

## 2. Re-computation comparison script (template)

Write `analysis/recompute/compare.py` that loads both values and appends rows to
`ledgers/RECOMPUTATION_AUDIT.csv`; never type the values by hand:

```python
import csv, json, math
from pathlib import Path

def record(stat_id, hyp, desc, primary, p_method, independent, i_method, atol=1e-6, rtol=1e-3):
    ok = math.isclose(primary, independent, rel_tol=rtol, abs_tol=atol)
    with Path("ledgers/RECOMPUTATION_AUDIT.csv").open("a", newline="") as fh:
        csv.writer(fh).writerow([stat_id, hyp, desc, primary, p_method, independent, i_method,
                                 atol, rtol, "match" if ok else "MISMATCH"])
    return ok
```

## 3. Claim–evidence audit

For every sentence with a citation, confirm: (a) the cited work says it (quote + location recorded),
(b) the strength matches ("shows" vs "suggests"), (c) the scope matches (crop, region, period),
(d) the citation is not a secondary citation of someone else's finding (cite the original).
Optional: K-Dense `scientific-writing/scripts/audit_claims.py` and
`peer-review/scripts/validate_claim_evidence.py` (run with `--help` first).

## 4. Reference existence audit

```bash
bibvet refs/refs.bib
academic-refchecker --paper manuscript/manuscript.md
```

Save outputs to `review/refcheck_<date>.txt`. Any unresolved reference is a blocker for S8.

## 5. Reproducibility re-run (S8 auditor)

From a clean clone: create the environment from the lock file, run `analysis/run_all.sh`, then
diff `results/` against the committed versions (byte-identical or within stated tolerances). Report
any difference as a major issue.
