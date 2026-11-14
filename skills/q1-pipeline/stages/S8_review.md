# S8: Adversarial Q1 review

**Goal:** find every reason a Q1 journal could reject the paper, and fix it before submission.

## Steps

1. Run the `q1-review` skill. It must use **fresh, independent reviewers** that did not write the
   paper: a new agent session, a subagent with no drafting history, or a different model. Reviewers get
   only: `manuscript/`, figures, `refs/refs.bib`, `.ros/core/Q1_RUBRIC.md`, the domain reporting
   checklist and the target journal's scope.
2. Panel: (a) methods/statistics expert, (b) domain expert, (c) handling editor (runs the desk-reject
   simulation first), (d) reproducibility auditor (tries to rerun `analysis/run_all.sh` from a clean
   clone and checks NUMBER_PROVENANCE by script).
3. Each reviewer writes major and minor issues to `review/ISSUES.csv` and a report (≥ 150 words) to
   `review/REVIEW_editor_vN.md`, `REVIEW_methods_vN.md`, `REVIEW_domain_vN.md`,
   `REVIEW_reproducibility_vN.md`. The gate requires all four.
4. The editor consolidates scores into `review/Q1_SCORECARD.csv` (every dimension, score 1–5, evidence,
   and the `reviewer` role that gave it; `self`/`author` are rejected as not independent).
5. Run the literature audit tools (see `q1-verify`): `academic-refchecker`, `bibvet`, and an
   adversarial PaperQA2 query "What evidence contradicts our main claims?" if allowed.
6. Fix loop: address each major issue (new analysis → back to S4/S5/S6 with deviations logged; text →
   S7). Mark `resolved` with a note, or `justified` with a written argument. Re-review the changed parts
   with a fresh reviewer.
7. Repeat until every dimension ≥ 4 and no major issue is open. Then `rosctl gate S8`.

## Human gate

The owner reads the reviews, the scorecard and the diff of changes, and runs `rosctl approve S8`.
Honest note for the owner: this is an internal standard; real reviewers may still disagree.
