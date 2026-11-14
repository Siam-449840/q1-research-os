# Pre-registered Analysis Protocol

<!-- Drafted by the agent in S2 from PROPOSAL.md + S1 findings. Approved and FROZEN by the owner with
`rosctl approve S2`. After freezing, edit ONLY the "Deviations" section at the bottom. -->

- **Version / date:** <v1, YYYY-MM-DD>
- **Linked proposal commit:** <git commit hash>

## 1. Research Questions

<RQ1, RQ2 ... exactly as in PROPOSAL.md, refined by S1 findings>

## 2. Hypotheses

<!-- For each: H#, statement, rival explanation, discriminating prediction, measurement,
Decision rule, smallest effect size of interest. Label confirmatory vs exploratory. -->

<H1 ... with Decision rule ...>

## 3. Data

<datasets (IDs from DATA_PROVENANCE), inclusion/exclusion rules, unit of analysis, time window, spatial extent>

## 4. Variables

<outcome(s), predictors, covariates, transformations, units, derivation code path>

## 5. Primary Analysis

<model specification, estimator, software + version, random seed(s), hyperparameter search space and budget>

## 6. Validation Strategy

<split design matched to dependence structure (spatial/temporal/grouped), leakage controls, metrics>

## 7. Robustness, Sensitivity and Ablations

<list each check and what result would weaken the conclusion>

## 8. Multiple Comparisons and Uncertainty

<correction method (e.g. Holm, BH-FDR), CI method (e.g. 2,000-sample bootstrap), reporting of effect sizes>

## 9. Stopping Rules and Missing Data

<when to stop tuning; how missing data/outliers are handled; what is NOT allowed (e.g. no re-splitting)>

## 10. Success Criteria

<what counts as support / no support for each hypothesis, consistent with the decision rules>

## 11. Deviations

<!-- Append-only after freeze. Format: YYYY-MM-DD | what changed | why | impact on conclusions. -->

None yet.
