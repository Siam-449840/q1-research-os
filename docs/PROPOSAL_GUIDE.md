# How to write a proposal that gets the best out of Q1 Research OS

The agent does 90–95 % of the work, but it can only be as good as its brief. `PROPOSAL.md` is that
brief: the single document that decides **what** is studied, **how** success is judged, and **what the
agent may decide alone**. An hour spent sharpening it saves weeks of work in the wrong direction.

Template: [`templates/project/PROPOSAL.md`](../templates/project/PROPOSAL.md) ·
Worked example: [`examples/agriculture-rice-yield-transfer/PROPOSAL.md`](../examples/agriculture-rice-yield-transfer/PROPOSAL.md) ·
Check it: `rosctl lint-proposal` · Get coaching: ask the agent to use the `q1-proposal` skill.

---

## 1. The ten principles

1. **One-sentence contribution first.** If you cannot finish "We show that ___, which matters because
   ___", you are not ready. Everything else serves this sentence.
2. **Specific beats impressive.** "Leave-one-zone-out RMSE of district Boro rice yield" is actionable;
   "advanced AI for food security" is not.
3. **Falsifiable hypotheses with decision rules.** Write in advance what result would count as support
   and what would not. This is what makes the analysis credible and lets the agent work without you.
4. **Name the rival explanation.** For every hypothesis, say what else could produce the same pattern
   and how the design tells them apart. Reviewers will think of it; make sure you did first.
5. **Validation that matches the data.** Spatial, temporal and grouped data need spatial, temporal and
   grouped validation. Random splits are the most common reason computational agriculture papers are
   rejected or later contradicted.
6. **Strong baselines, named.** The strongest published method plus a simple reference baseline. A
   method that beats only a straw man is not a contribution.
7. **Data you have already opened.** List URL, version, license, coverage and access status. Unverified
   data access is the number one reason projects stall.
8. **Figure-first planning.** List the 3–6 figures that would make the paper and the one message each
   carries. If the figures do not tell the story, the paper will not either.
9. **Plan for the null result.** Say what you will publish if the hypotheses fail. A design that is
   informative either way is a strong design.
10. **Reserve your decisions explicitly.** Section 12 tells the agent where it must stop and ask you.
    Everything not reserved, it will do autonomously.

## 2. Section-by-section guidance

| Section | What excellent looks like | Common mistakes |
|---|---|---|
| 0 Metadata | Domain pack set; 2–3 ranked journals with a one-line fit reason; limits; communication language; realistic time budget | No journals ("decide later") → the agent cannot match scope or format |
| 1 Contribution | ≤ 60 words; names the question, evidence and why it matters | "We apply X to Y" (method-on-region) |
| 2 Problem & significance | Who is affected, what decision depends on it, magnitude (to be verified in S1) | Generic "food security is important" |
| 3 Knowledge & gap | Known / contested / missing; gap typed and stated as a checkable claim; closest works you know | "No one has studied this" without a search |
| 4 RQs & hypotheses | 1–3 RQs; each H with rival, discriminating prediction, measurement, decision rule, smallest effect of interest | Questions without hypotheses; untestable claims |
| 5 Data | Table with URL, version, license, coverage, unit, issues, access status | "Satellite data" with no product, version or license |
| 6 Methods & validation | Primary analysis, baselines, split design, uncertainty, robustness, multiplicity, compute | "We will use deep learning" with no validation design |
| 7 Expected results & figures | 3–6 figures with messages; what falsifies; the null-result paper | Promising results ("will achieve 95% accuracy") |
| 8 Threats | ≥ 3 specific threats (construct, internal, external, conclusion) with mitigations | "Limited data" |
| 9 Ethics & sharing | Licenses, personal data, what will be shared, archive DOI, AI policy | Ignored until submission |
| 10 Definition of done | Objective: gates passed, word limits, one-command reproduction | "When the paper is good" |
| 11 Constraints | Budget, paid APIs (yes/no), hardware, max download, institutional access | Missing, so the agent guesses |
| 12 Owner decisions | Concrete list of what always needs your approval | Missing, so the agent either asks too much or too little |

## 3. Weak → strong examples

**Contribution**

- Weak: "We use machine learning to predict wheat yield in Punjab."
- Strong: "We test whether wheat yield models trained on irrigated districts transfer to rain-fed
  districts in Punjab, quantify the accuracy lost, and show which predictors cause the failure."

**Hypothesis**

- Weak: "Remote sensing improves yield prediction."
- Strong: "H1: Adding Sentinel-2 red-edge indices reduces leave-one-year-out RMSE relative to a
  weather-only model. Rival: improvement comes from the extra years of data, not the indices.
  Discriminating prediction: the improvement persists when both models use identical years. Decision
  rule: supported if the 95% block-bootstrap CI of ΔRMSE lies below −5%. Smallest effect: 5%."

**Validation**

- Weak: "80/20 train-test split."
- Strong: "Leave-one-region-out and leave-one-year-out cross-validation; hyperparameters tuned by nested
  CV within the outer training folds; random K-fold reported only to quantify optimism."

## 4. How the agent uses each section

| Section | Used in stages |
|---|---|
| Contribution, gap | S1 novelty search; S7 Introduction; S9 cover letter |
| RQs and hypotheses | S2 protocol (frozen); S5 re-computation coverage; S7 Results structure |
| Data | S3 downloads, provenance and licenses |
| Methods and validation | S2 protocol; S4 code; S8 methods review |
| Figures | S6 storyboard |
| Threats | S2 controls; S7 Limitations; S8 review |
| Journals | S0 fit check; S7 format; S9 package |
| Constraints and owner decisions | every stage (when to stop and ask) |

## 5. Pre-flight checklist (before you hand over to the agent)

- [ ] `rosctl lint-proposal` passes with no blockers (aim for a score ≥ 90).
- [ ] I have opened every dataset at least once and know its license.
- [ ] I have read at least 3 of the closest papers myself.
- [ ] I have read 2–3 recent papers in each target journal.
- [ ] My hypotheses would convince me if they failed, not only if they succeeded.
- [ ] I know what I will publish if the main hypothesis fails.
- [ ] Section 12 lists everything I want to decide myself.

## 6. Prompts to start the agent

Claude Code (in the project folder):

```
Use the q1-pipeline skill. Read AGENTS.md and PROPOSAL.md, run `rosctl status`, and work through the
stages. Stop at every human gate and give me the checkpoint in my communication language.
```

Antigravity (open the project folder as the workspace):

```
Follow AGENTS.md. Use the q1-pipeline skill in .agents/skills. Start with `rosctl status` and continue
from the current stage; stop at each human gate with a checkpoint.
```
