# S10: Revision and rebuttal

## Steps

1. The owner pastes the decision letter into `review/DECISION_LETTER.md`.
2. Split it into atomic comments. In `review/RESPONSE_TO_REVIEWERS.md`, for every comment write:

   ```
   **Comment R1.3:** <verbatim reviewer text>
   **Response:** <thank briefly; agree / partly agree / respectfully disagree; what we did>
   **Change:** <section, line or figure; quote the new text>
   ```

3. Classify each: text fix / new analysis / new data / disagreement. New analyses go through S4–S6
   with a `## Deviations` entry ("added at reviewer request") and new provenance rows.
4. Disagree only with evidence (data, citations with CLAIM_SUPPORT rows), never with tone.
5. Re-run `rosctl gate S7` and a fresh `q1-review` on the changed parts.
6. Produce a tracked-changes version for the journal when the owner asks.
7. `rosctl gate S10`. The owner submits the revision personally.
