# S2: Protocol and pre-registration freeze

**Goal:** fix the confirmatory analysis BEFORE seeing results, so findings cannot be p-hacked or
HARKed (hypothesising after results are known). Reviewers trust pre-specified analyses.

## Steps

1. Draft `protocol/PROTOCOL.md` from `PROPOSAL.md` + the S1 verdict. Fill every section of the template.
2. For each hypothesis write the full chain: statement → rival explanation → discriminating prediction →
   measurement → **Decision rule** → smallest effect size of interest. Label each analysis
   **confirmatory** or **exploratory**.
3. Validation design must respect the dependence structure (`.ros/domain/PITFALLS.md`): spatial,
   temporal, grouped or hierarchical data never get plain random K-fold for the headline result.
4. Specify: baselines and their tuning budget (equal effort), metrics, uncertainty method, multiplicity
   control, robustness/ablation list, missing-data rules, stopping rules for tuning, seeds.
5. Power / precision: if feasible, estimate whether the sample can detect the smallest effect of
   interest (simulation or analytic). If not feasible, say so and explain.
6. Pick the reporting guideline now (domain pack `REPORTING.md`) and make sure the protocol collects
   everything it requires.
7. Optional but strong: if the K-Dense `hypothesis-generation` skill is installed, run its
   `generate_preregistration_scaffold.py` / `validate_hypothesis_schema.py` / `check_falsification_controls.py`
   and fix what they report.
8. `git add protocol/PROTOCOL.md && git commit -m "protocol: draft for freeze"`, then `rosctl gate S2`.

## Human gate

Stop. Explain the protocol to the owner in plain language: what will be tested, how, what counts as
support, and what is exploratory. The owner runs `rosctl approve S2`. This records the SHA-256 of
everything above `## Deviations`; any later change there fails every subsequent gate.

## After the freeze

Changes go only into `## Deviations` as `YYYY-MM-DD | what | why | impact`, and every deviation is
reported in the manuscript's Methods.

Label every pre-registered analysis `A1`, `A2`, ... in the protocol (the S2 gate blocks an unfrozen protocol
without labels). After running them, give each a row in `ledgers/PROTOCOL_EXECUTION.csv`: `done` with the
results file and exact locator, or `deviation` explained under `## Deviations`. `rosctl check execution` (C59).

## v1.2 method requirements (enforced)

`rosctl` scans the protocol and blocks when a method is named without its safeguard: ANOVA without the
sum-of-squares type [E116] or assumption checks [E40]; post-hoc tests without error-rate control [E42,E43];
mixed models without stated fixed and random effects [E117]; log transforms without back-transformation and
zero handling [E118]; spatial/temporal/repeated data without a dependence strategy [E119]; block or factorial
designs without the experimental unit [E24,E25] and an interaction plan [E45]; power analysis without the
effect size and its source [E26]; Likert data without ordinal handling [E121]; human participants without
ethics/consent [E124]; causal questions without identification [E23,E27]; ML without seeds, repeated runs,
nested tuning, baselines and imbalance-aware metrics [E53-E57]; public benchmarks without a contamination
statement [E109]; genomics without pinned genome/annotation versions [E114]; repository mining without
bot/fork/duplicate filters [E123]. At `rosctl approve S2` the owner confirms H06-H09.
