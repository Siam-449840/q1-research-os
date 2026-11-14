# S0: Proposal intake and lint

**Goal:** make sure the brief is specific enough that 90 % autonomous work will go in the right direction.
Garbage in, garbage out: a vague proposal is the single biggest threat to a Q1 outcome.

## Steps

1. Read `PROPOSAL.md` completely, then `.ros/domain/DOMAIN.md`.
2. Run `rosctl lint-proposal`. Record the score.
3. Beyond the linter, judge the proposal as a demanding PI would. For each item, write a finding:
   - Is the contribution one clear sentence a Q1 editor would care about? Is it more than "apply method
     M to region R"? If it is only that, propose 2–3 sharper framings (new question, transfer test,
     mechanism, decision-relevant metric).
   - Are hypotheses falsifiable, with rival explanations and decision rules?
   - Is the validation strategy matched to the data's dependence structure (see
     `.ros/domain/PITFALLS.md`)?
   - Are the baselines the strongest current ones (not straw men)?
   - Is every dataset realistically accessible under the stated constraints?
   - Do the target journals actually publish this type of paper?
4. Do **not** rewrite the owner's intent. Use the `q1-proposal` skill to propose concrete edits as a
   diff or a list, and ask the owner to accept/reject each. The owner edits `PROPOSAL.md` (or tells you
   to apply the accepted edits).
5. Re-run `rosctl lint-proposal` until it has no blockers, then `rosctl gate S0`.

## Output

- A short "Proposal review" checkpoint (what is strong, what is risky, accepted edits).
- `ledgers/DECISION_LOG.csv` rows for any framing decision.

## Failure modes

- Accepting a "new region, same method" contribution without challenge.
- Silently changing the research question.
- Starting S1 with datasets that have never been opened.
