# Research Proposal: <working title>

<!--
HOW TO USE THIS FILE
- This is the ONLY document the AI agent treats as your intent. Everything it does traces back here.
- Replace every <angle-bracket placeholder>. Delete these HTML comments if you like (they are ignored).
- Be concrete: numbers, names, URLs, decision rules. Vague input produces generic output.
- Check readiness at any time:  rosctl lint-proposal
- Full guidance and a worked example: docs/PROPOSAL_GUIDE.md and examples/
-->

## 0. Metadata

- **Working title:** <specific, contains the main variable, method and setting>
- **Discipline / subfield:** <e.g. Agriculture / Remote sensing of crop yield>
- **Domain pack:** <agriculture | software-engineering | _template | your-pack>
- **Research type:** <computational / secondary-data / modelling / meta-analysis / ...>
- **Target journals (ranked):**
  1. <Journal A>: <why it fits: 1 line>
  2. <Journal B>: <why it fits>
  3. <Journal C>: <why it fits>
- **Article type and limits:** <e.g. Research article, ≤ 8,000 words, abstract ≤ 250 words>
- **Owner(s):** <name(s), role>
- **Communication language (agent → owner):** <e.g. English | বাংলা>
- **Deadline / time budget:** <e.g. 10 weeks, 15 h/week>

## 1. Contribution Statement

<!-- ONE or two sentences, <= 60 words. Pattern: "We show/quantify/develop X for Y using Z, which
matters because W." If you cannot write this, you are not ready to start. -->

<contribution sentence>

## 2. Problem and Significance

<!-- Who has the problem? What decision, cost, risk or scientific belief depends on solving it?
Give magnitudes ("affects N ha / N farmers / N USD / N% of variance"), each to be verified in S1. -->

<problem and significance>

## 3. State of Knowledge and Gap

<!-- What is established, what is contested, what is missing. Name the closest works you already know
(author, year, DOI if known); the agent will verify and expand to >= 10 in S1.
Classify the gap: evidence gap | method gap | data/coverage gap | contradiction | transferability gap.
State the gap as something checkable: "No study has X under Y" will be tested in S1. -->

<state of knowledge, known closest works, gap type and gap statement>

## 4. Research Questions and Hypotheses

<!-- 1-3 RQs. For EVERY hypothesis give all five lines. A hypothesis without a rival explanation and a
decision rule cannot be falsified, and reviewers will notice. -->

**RQ1:** <question>

- **H1:** <directional, testable statement>
  - **Rival explanation:** <what else could produce the same pattern>
  - **Discriminating prediction:** <what we would observe if H1 is true but the rival is false>
  - **Measurement:** <variable, unit, dataset, aggregation>
  - **Decision rule:** <e.g. "supported if the 95% CI of ΔRMSE excludes 0 and ΔRMSE ≤ −5%">
  - **Smallest effect size of interest:** <e.g. 5% RMSE reduction; justify>

## 5. Data Sources

<!-- Every dataset: URL, version or access date, license, coverage, unit of analysis, known issues,
access status. Prefer data you have ALREADY opened. Unverified data access is the #1 cause of stalled
projects. -->

| ID | Dataset | URL | Version / date | License | Coverage (space, time) | Unit | Known issues | Access status |
|---|---|---|---|---|---|---|---|---|
| D1 | <name> | <dataset URL> | <v / date> | <license> | <coverage> | <unit> | <issues> | <downloaded / API / request> |

## 6. Methods and Validation

<!-- Primary analysis; baselines (strongest published + simple reference); validation strategy that
matches the dependence structure of your data (spatial, temporal, grouped); uncertainty quantification;
robustness/sensitivity/ablation plan; software stack. -->

- **Primary analysis:** <model / estimator / pipeline>
- **Baselines:** <strongest published method>; <simple reference baseline>
- **Validation strategy:** <e.g. leave-one-region-out and leave-one-year-out cross-validation>
- **Uncertainty:** <bootstrap CIs / Bayesian posterior intervals / ensemble spread>
- **Robustness and sensitivity:** <alternative specifications, ablations, sensitivity to key choices>
- **Multiplicity:** <how multiple tests/comparisons are controlled>
- **Software and compute:** <Python/R, key libraries, hardware limits>

## 7. Expected Results and Planned Figures

<!-- Figure-first thinking: list the figures that would make the paper, each with the ONE message it
must carry. Also say which result would falsify your hypotheses and what you would publish then. -->

- **Fig. 1:** <message>
- **Fig. 2:** <message>
- **Fig. 3:** <message>
- **If hypotheses fail:** <what the null/negative result paper would say and why it still matters>

## 8. Threats to Validity

- <threat 1 (construct / internal / external / conclusion)>: <mitigation>
- <threat 2>: <mitigation>
- <threat 3>: <mitigation>

## 9. Ethics, Licensing and Data Sharing

<!-- Human/animal data? Personal or location-sensitive data? License compatibility? What will be shared
(code license, processed data, archive DOI)? Journal AI-use policy? -->

<ethics, licensing and sharing plan>

## 10. Definition of Done

<!-- Objective conditions. Example: "All rosctl gates S0-S9 pass; manuscript <= 8,000 words; all
figures reproducible with one command; Zenodo-ready archive built." -->

<definition of done>

## 11. Constraints and Resources

<!-- Budget (e.g. zero-cost only), paid APIs allowed?, hardware (RAM/GPU/disk), max download size,
tools you must or must not use, institutional access (library, Turnitin). -->

<constraints>

## 12. Decisions Reserved for the Owner

<!-- What the agent must ALWAYS ask you before doing. Gates S1/S2/S8/S9 are always yours. -->

- <e.g. any download > 2 GB>
- <e.g. adding a new dataset or changing the primary outcome>
- <e.g. choosing the final target journal>
