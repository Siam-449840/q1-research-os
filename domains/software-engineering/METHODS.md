# Methods and expected baselines (empirical SE)

- **Repository mining:** sampling frames that are reproducible (query + date), bot/fork filtering,
  identity merging, time-aware analysis (no future information).
- **Statistics:** non-parametric tests (Wilcoxon, Mann–Whitney), effect sizes (Cliff's delta, Vargha–
  Delaney A12), Scott–Knott ESD for ranking, mixed-effects models for repeated measures across projects,
  survival analysis for time-to-event (e.g. issue resolution), regression with project fixed effects.
- **Testing research:** differential testing between implementations; metamorphic relations derived
  from domain laws; mutation analysis to assess test adequacy; fuzzing with fixed time budgets and
  repeated trials (≥10 runs, report variance).
- **Prediction (defect/effort):** time-aware splits (train on past releases, test on future), cross-
  project validation, effort-aware metrics, tuned baselines.
- **LLM-for-code studies:** fixed model versions and dates, prompts released, multiple runs, contamination
  checks (benchmark released before model cutoff?), cost reporting.
- **Qualitative coding of artefacts:** codebook, two coders, inter-rater agreement (Cohen's κ /
  Krippendorff's α), disagreement resolution.
- **Expected baselines:** simple heuristics, prior state-of-the-art tools on the same subjects, random
  baselines for search/prediction.
