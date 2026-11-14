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
