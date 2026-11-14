---
name: q1-proposal
description: Help a researcher write or sharpen PROPOSAL.md for Q1 Research OS - interview mode for a blank proposal, critique mode for a draft, contribution sharpening, hypothesis chains with decision rules, data feasibility and validation design. Use when the user says "help me write my proposal", "review my proposal", "is my idea Q1?", or when `rosctl lint-proposal` fails.
---

# Proposal coach

The proposal is the steering wheel of the whole pipeline. Your job is to make it **specific,
falsifiable, feasible and ambitious**, without replacing the owner's intent.

## Mode A: interview (blank or near-blank proposal)

Ask in short rounds (max 4 questions per round), in the owner's language:

1. **Problem:** Who suffers from not knowing this? What decision would change? How big is it?
2. **Data:** Which datasets have you opened already? Coverage, unit, license?
3. **Question:** If the study works perfectly, what one sentence will you be able to say?
4. **Competition:** Which 3 papers are closest? What did they not do?
5. **Method:** What is the strongest current method? What simple baseline must be beaten?
6. **Validation:** Will results need to work in a new place, a new year, a new population?
7. **Venue:** Which 2–3 journals publish papers like this? Have you read a recent one?
8. **Constraints:** Budget, hardware, deadline, tools you cannot use?

Then fill `PROPOSAL.md` section by section from the answers, marking anything you inferred with
`[VERIFY: ...]` (the linter blocks until the owner resolves it).

## Mode B: critique (existing draft)

1. Run `rosctl lint-proposal`; fix structural blockers first.
2. Score the draft against these questions and give one concrete improvement for each weakness:
   - **Contribution:** is it more than "method M on region R"? Offer sharper framings, for example
     a transferability test, a mechanism, a decision-relevant metric, an uncertainty or bias analysis,
     a benchmark, or a negative result that corrects the literature.
   - **Hypotheses:** each has rival explanation, discriminating prediction, measurement, decision rule,
     smallest effect size of interest?
   - **Validation:** matches the data's dependence structure (`.ros/domain/PITFALLS.md`)?
   - **Baselines:** strongest published + simple reference?
   - **Data feasibility:** URLs, licenses, sizes, access verified?
   - **Figures:** do the planned figures tell the story without text?
   - **Venue fit:** do the target journals publish this design?
3. Present edits as a numbered list (old → new). Apply only those the owner accepts.

## Contribution sharpening patterns

| Weak | Stronger |
|---|---|
| "We apply random forest to predict yield in district X." | "We test whether yield models trained in one agro-ecological zone transfer to others, and quantify how much accuracy is lost and why." |
| "We analyse the effect of climate on production." | "We separate the contribution of heat vs. drought to yield shocks, using a design that rules out technology trend and price effects." |
| "We review studies on topic T." | "We meta-analyse N studies to estimate effect E with heterogeneity, and identify which design choices explain divergent results." |

## Output

A lint-clean `PROPOSAL.md`, plus a short list of the remaining risks the owner accepted.
