---
name: q1-verify
description: Verification toolkit for Q1 Research OS - number provenance, citation/claim support, independent re-computation audits, reference existence checks and reproducibility re-runs. Use in S5, S7 and S8, whenever a number or citation is added to the manuscript, or when the user asks "check everything" / "is this traceable?".
---

# Verification toolkit

Verification is done by **scripts and second sources**, never by re-reading and agreeing with yourself.

## 1. Built-in checks (rosctl)

```bash
rosctl check numbers      # every manuscript number ↔ NUMBER_PROVENANCE.csv ↔ value present in results file
rosctl check citations    # every [@key] in refs.bib, has DOI/URL, and a CLAIM_SUPPORT row
rosctl check recompute    # RECOMPUTATION_AUDIT within tolerance; every hypothesis covered; methods differ
rosctl check manuscript   # required sections, no placeholders, abstract length
rosctl check review       # scorecard complete, all >= 4, no open major issue
```

How `check numbers` decides: it extracts decimals, percentages and integers > 10 (except years and
anything inside `code spans`, `[@...]`, `[Source: ...]`, URLs, or figure/table/section labels) and
requires a matching `value` in `ledgers/NUMBER_PROVENANCE.csv`; then it confirms that value appears
(allowing for rounding, and fraction ↔ percent) in the referenced results file.

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
