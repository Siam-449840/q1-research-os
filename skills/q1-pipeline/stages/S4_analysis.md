# S4: Analysis pipeline (tested, logged, leakage-free)

**Goal:** production-quality research code that implements the frozen protocol exactly, is tested,
and regenerates every result with one command.

## Engineering standards

- Python via `uv` (`uv init`, `uv add <pkg>`, commit `uv.lock`) or R via `renv` (commit `renv.lock`).
- Pin versions. Fix seeds (from the protocol) and record them in outputs.
- Structure: `analysis/00_get_*`, `01_data_audit`, `02_process`, `03_features`, `04_models`,
  `05_evaluate`, `06_robustness`, `07_figures`, plus `analysis/run_all.sh` (or `Makefile`).
- Pure functions in a module (e.g. `analysis/lib/`), thin scripts calling them.
- Config in one file (`analysis/config.yaml` or `.toml`): paths, seeds, hyperparameter grids. No magic numbers.
- Outputs: machine-readable (`.csv`, `.json`, `.parquet`) in `results/<step>/`, each with the git
  commit and config hash written alongside. Never hand-edit `results/`.

## Steps

1. **Tests first for the risky parts** in `analysis/tests/test_*.py` (pytest):
   - the split function: no unit (location / year / group) appears in both train and test;
   - feature code: no future or target information leaks into features (time ordering, target encoding);
   - metric functions against hand-computed toy cases;
   - processing invariants (units, ranges, row counts, no duplicated keys).
2. Implement processing → features → baselines → primary model → evaluation, following the protocol
   exactly. Anything not in the protocol is **exploratory** and goes in a separate folder and section.
3. **Pilot** on a small subset; check runtime and memory against PROPOSAL §11.
4. **Full run** via `rosctl run -- bash analysis/run_all.sh`. Then `rosctl run -- uv run pytest analysis/tests`.
5. Robustness, sensitivity and ablations exactly as listed in the protocol (`06_robustness`).
6. If a run fails: read the traceback, fix the root cause, re-run. Never write placeholder results.
7. Determinism check: re-run the primary model once; results must be identical (or within a stated
   tolerance for GPU non-determinism). Record in `ledgers/DECISION_LOG.csv`.
8. Any protocol change → append to `## Deviations` with reason BEFORE running it.
9. **Split manifest (leakage audit).** The code that builds cross-validation folds must also write
   `results/splits/<design>.csv` with columns `fold,split,group` (one row per fold × split × group;
   `split` is `train`, `test` or `val`; `group` is the unit that must not leak: site, region, year,
   farm, genotype family ...). `rosctl` blocks the gate if any group appears in both train and test of
   the same fold. For designs without folds (e.g. causal panel models), write
   `results/splits/NOT_APPLICABLE.md` (≥ 40 words) explaining how independence is ensured instead.
10. `rosctl gate S4`.

## Domain specifics

Read `.ros/domain/METHODS.md` and `.ros/domain/PITFALLS.md` before writing model code. They list the
standard methods, the expected baselines and the leakage traps of the field.

## Failure modes

- Tuning hyperparameters on the test fold.
- Random K-fold on spatial/temporal/grouped data for the headline number.
- Different tuning effort for baselines vs the proposed method.
- Notebook-only code that cannot be re-run top to bottom.

## v1.2 requirements (enforced)

- Pin the environment (`uv.lock`, `renv.lock`, `poetry.lock` or `requirements.txt` with `==`) [E57] and run
  `rosctl verify-deps` BEFORE installing: unknown or brand-new (< 90 days) packages block [E105].
- Every file in `results/`, `manuscript/figures/` and `manuscript/tables/` must be produced by a logged
  `rosctl run`; hand-edited, copied or stale outputs block [E31,E49,E50,E102].
- No synthetic fallbacks, silent `except: pass` or global warning suppression; legitimate randomness is seeded
  and annotated `# ros: allow-random <reason>` [E100,E101].
- Numeric-coded treatments/blocks/years declared `coded_numeric=yes` in the schema must be wrapped as factors
  in model formulas (`C(treatment)`, `factor(block)`) [E115].
- When S4 passes, `analysis/tests/` and `analysis/eval/` are locked. If a test fails later, fix the code, not
  the test; only the owner can run `rosctl relock-tests --reason ...` [E99].
