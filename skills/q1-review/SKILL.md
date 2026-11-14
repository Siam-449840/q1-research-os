---
name: q1-review
description: Independent adversarial Q1 review panel for Q1 Research OS - editor desk-reject simulation, methods/statistics reviewer, domain reviewer and reproducibility auditor, scored on the 15-dimension Q1 rubric with evidence. Use in S8, after major revisions, or when the user asks "would this get into a Q1 journal?" / "review my paper harshly".
---

# Q1 review panel

## Independence is mandatory

The author-agent cannot review its own work credibly. Run each reviewer in a **fresh context**:
a new session, a subagent with no drafting history, or a different model. Give reviewers only:
`manuscript/`, `manuscript/figures/`, `refs/refs.bib`, `.ros/core/Q1_RUBRIC.md`,
`.ros/domain/REPORTING.md`, `.ros/domain/PITFALLS.md`, and the target journal's aims & scope.
Do NOT give them PROPOSAL.md, chat history or the author's opinions.

## Reviewer prompts

**Editor (desk-reject simulation):**
> You are the handling editor of <journal>. You have 5 minutes. Read the title, abstract, first figure,
> cover letter and reference list. Answer the six desk-reject questions in Q1_RUBRIC.md with yes/no and
> one-line reasons. Decide: desk reject / send to review. Then list the three things most likely to
> make reviewers reject it.

**Reviewer 1: methods & statistics:**
> You are a senior methodologist who has rejected many papers for leakage, weak baselines and
> overclaiming. Check the design against PITFALLS.md, the validation strategy, baselines and tuning
> parity, uncertainty, multiplicity, assumptions, and whether conclusions follow from the numbers.
> List MAJOR and MINOR issues with location and a concrete fix.

**Reviewer 2: domain expert:**
> You are a leading researcher in <subfield>. Judge significance, novelty against the literature you
> know, positioning, physical/biological plausibility of results, and practical implications. Name any
> missing key reference (with DOI if you are sure; otherwise describe it, never invent one).

**Reviewer 3: reproducibility auditor:**
> From a clean clone, rebuild the environment, run analysis/run_all.sh, and compare results/. Run
> `rosctl check numbers` and `rosctl check citations`. Check data availability statements against
> licenses. Report every failure.

## Output files

- `review/REVIEW_<role>_v<N>.md`: full report per reviewer.
- `review/ISSUES.csv`: `issue_id, reviewer, severity (major|minor), location, issue, action,
  status (open|resolved|justified), resolution_note`.
- `review/Q1_SCORECARD.csv`: editor consolidates one score (1–5) per rubric dimension with evidence.

## Scoring discipline

- Score what is on the page, not what the authors intend.
- A 5 needs evidence a skeptic would accept. When in doubt, score lower.
- Never edit the scorecard to pass the gate; fix the paper, then re-review with a fresh reviewer.

Optional: K-Dense `peer-review` (scripts `generate_review_scaffold.py`,
`audit_statistics_reproducibility.py`, `audit_citations.py`), `scholar-evaluation`, claude-scholar
`paper-self-review`.
