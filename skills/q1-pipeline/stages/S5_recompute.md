# S5: Independent re-computation

**Goal:** catch silent bugs. Every headline statistic is computed a second time by an independent
route. If the two disagree, the paper is not ready.

## Steps

1. List every confirmatory statistic per hypothesis (effect sizes, metrics, test statistics, CIs).
2. For each, choose an independent route (pick the strongest available):
   - **Fresh-session re-implementation (best):** a new agent session that has NOT seen `analysis/`
     receives only `protocol/PROTOCOL.md`, `data/DATA_CARD.md` and the processed inputs, and writes
     `analysis/recompute/` from scratch.
   - **Different library:** e.g. `statsmodels` vs `scipy.stats` / `pingouin`; `scikit-learn` metric vs a
     hand-written NumPy metric; R vs Python for mixed models (`lme4` vs `statsmodels` MixedLM).
   - **Different algorithm:** analytic CI vs bootstrap CI; closed form vs numerical.
3. Run with `rosctl run -- ...`. Write both values to `ledgers/RECOMPUTATION_AUDIT.csv`:
   `stat_id, hypothesis_id, description, primary_value, primary_method, independent_value,
   independent_method, abs_tolerance, rel_tolerance, status`.
   Choose tolerances before comparing (e.g. 1e-6 for deterministic, 1e-2 relative for bootstrap).
4. Any mismatch → STOP. Find which one is wrong. Fix the bug, re-run S4 outputs, re-compute. Record the
   bug and fix in `ledgers/DECISION_LOG.csv` (this is valuable evidence of rigour).
5. Use the `q1-verify` skill for the comparison script.
6. `rosctl gate S5`.
