# Q1 Rubric: what top-quartile editors and reviewers actually check

Scores are 1–5. **Every dimension must reach ≥ 4 with written evidence before S8 can pass.**
Each row in `review/Q1_SCORECARD.csv` uses the exact `dimension` id below.

| id | Dimension | 3 = "major revision" | 5 = "accept" |
|---|---|---|---|
| `significance` | Why it matters | Interesting to a niche | Changes a decision, method or belief that a broad community cares about; stakes quantified |
| `novelty` | What is new | Incremental: new dataset/region, same method, same question | New question, new evidence type, or new method whose gain is demonstrated, not asserted |
| `positioning` | Relation to closest work | Related work listed, not compared | Closest 10 works explicitly contrasted on question, data, method and result; gap is evidenced |
| `design_validity` | Internal validity | Plausible confounds unaddressed | Design rules out the main rival explanations (controls, identification strategy, leakage-free splits) |
| `external_validity` | Generalisation | Single site / year / split | Tested on held-out locations, years or populations; transfer limits stated |
| `statistical_rigor` | Inference | p-values only, assumptions unchecked | Effect sizes with uncertainty, assumptions checked, multiplicity handled, confirmatory tests separated from exploration |
| `baselines` | Comparisons | Weak or straw-man baselines | Strongest published method + simple reference baseline, tuned with equal effort |
| `robustness` | Sensitivity | One configuration | Ablations, sensitivity to key choices, alternative specifications; conclusions survive |
| `reproducibility` | Can others redo it | Code "available on request" | Public code + data (or exact access steps), pinned environment, seeds, one-command rerun, archived DOI |
| `reporting_standards` | Checklist compliance | Ad hoc | Domain reporting guideline (TRIPOD+AI, STROBE, PRISMA 2020, REFORMS, MIAPPE, ODD, ...) completed and attached |
| `clarity` | Writing | Reader must work to find the contribution | Contribution clear in title, abstract and first paragraph; each section answers one question |
| `figures` | Visual evidence | Default plots, unreadable | Each figure makes one point, colour-blind safe, ≥ 300 dpi, uncertainty shown, self-contained caption |
| `limitations_honesty` | Candour | Generic limitations paragraph | Specific threats (construct, internal, external, conclusion) with their likely direction of bias |
| `implications` | So what | Speculative recommendations | Implications follow from the evidence and are bounded by it |
| `journal_fit` | Venue | Scope stretch | Matches aims & scope, recent articles, format, length and AI-use policy of the target journal |

## Desk-reject simulation (run before the full review)

An editor spends about 5 minutes on title, abstract, cover letter, first figure and references. The
paper is desk-rejected if any answer is "no":

1. Is the question within the journal's stated scope, and similar to papers it published in the last 3 years?
2. Can the contribution be stated in one sentence from the abstract alone?
3. Is there a quantitative headline result with uncertainty?
4. Does the method look current (not superseded by work the editor knows)?
5. Are references recent (a meaningful share from the last 5 years) and from credible venues?
6. Is the English clear enough that review is not a waste of reviewers' time?

## Common reasons Q1 papers are rejected (check each)

- "So what?": significance asserted but not demonstrated.
- Novelty claim contradicted by a paper the reviewer knows (S1 exists to prevent this).
- Data leakage or optimistic validation (random splits on spatial, temporal or grouped data).
- Weak baselines or untuned competitors.
- Overclaiming causality from observational data.
- Results not reproducible; code or data unavailable.
- Statistics without effect sizes, uncertainty or multiplicity control.
- Discussion repeats results instead of interpreting them against prior work.
