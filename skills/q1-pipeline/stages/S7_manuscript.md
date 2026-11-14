# S7: Evidence-bound manuscript

**Goal:** a complete, journal-formatted draft in which every number is provenanced, every citation is
verified and supports its sentence, and the contribution is unmistakable.

## Writing order (do not change)

Methods → Results → Discussion (incl. Limitations) → Introduction → Conclusion → Abstract → Title →
Keywords / Highlights → statements (data, code, AI use, CRediT, competing interests, funding).

## Section recipes

- **Methods:** enough detail to replicate: data (IDs, versions, access dates), preprocessing, models,
  hyperparameter search, validation design, metrics, statistics as pre-registered, software versions
  (in `code spans`), seeds, hardware, and a "Deviations from protocol" paragraph. Cite the reporting
  guideline you followed.
- **Results:** one subsection per RQ. First sentence answers the RQ. Then numbers with uncertainty and
  figure/table references. No interpretation beyond the numbers. Exploratory results clearly labelled.
- **Discussion:** principal findings → comparison with the closest work (agree / disagree and why) →
  mechanisms → implications bounded by the evidence → limitations (construct, internal, external,
  conclusion validity, with the likely direction of bias) → future work.
- **Introduction:** stakes (quantified, cited) → what is known → the evidenced gap (from
  NOVELTY_VERDICT) → contributions as 2–4 bullets → roadmap. Keep it to 4–6 paragraphs.
- **Abstract:** context, aim, data, method, 2–3 key numbers with uncertainty, meaning. Within limit.
- **Title:** specific; includes the main variable, approach and setting; no hype.

## Mechanics

1. Draft ≤ 800 words at a time in `manuscript/manuscript.md` (or one file per section; files starting
   with `_` are ignored by checks).
2. While drafting, bind sources: `[@citekey]` or `[Source: results/<file>]`. Copy numbers from results
   files, never from memory.
3. After each chunk:
   - add rows to `ledgers/NUMBER_PROVENANCE.csv` (`number_id, value, manuscript_location,
     results_file, locator, script`), value written exactly as in the text (e.g. `0.82`, `12.5%`).
     The **locator is mandatory** and must point at exactly one place: `model=rf:rmse` (CSV row whose
     `model` is `rf`, column `rmse`), `rmse` (CSV with one data row), `$.h1.ci.0` (JSON path), or
     `line:12` (text file). The text value must be a correct rounding of that exact cell;
   - add rows to `ledgers/CLAIM_SUPPORT.csv` for each citation (`evidence_location`, short
     `evidence_quote`, `support_level` = `supports | partially_supports | contrasts`);
   - run `rosctl check numbers`, `rosctl check citations` and `rosctl check stats`; fix everything.
     Report test results in APA style (`t(23) = 2.45, p = .021`, `F(2, 57) = 4.10, p = .022`,
     `χ2(1) = 3.84, p = .050`) so `check stats` can recompute each p-value from the statistic and
     degrees of freedom; a DECISION ERROR means the reported significance is wrong.
4. Language: clear, precise, active voice where natural, no hype words, consistent terminology, tense
   conventions (past for what you did, present for established facts). Optional: claude-scholar
   `writing-anti-ai` and K-Dense `scientific-writing` (its `audit_claims.py`, `check_consistency.py`,
   `lint_manuscript.py`).
5. Fill the domain reporting checklist (`.ros/domain/REPORTING.md`) and save it to
   `manuscript/_reporting_checklist.md` (ignored by number checks, attached as supplement).
6. Export for the journal when the owner asks (pandoc → .docx / journal LaTeX template).
7. `rosctl gate S7`.

## Failure modes

- Rounding a number differently in abstract and results.
- "Previous studies have shown [@a; @b; @c]" where only one actually shows it.
- Discussion that only restates results.
- Limitations that are generic ("more data is needed").
