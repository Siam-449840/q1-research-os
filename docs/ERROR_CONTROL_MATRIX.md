# 136-Error Control Matrix

Generated from `core/ERROR_CONTROLS.csv` and `core/CONTROLS.csv` by `bin/gen_matrix_doc.py`. `tests/test_controls.py` fails if any error lacks a control, or a control names a function or test that does not exist.

- **C** controls are code: fail-closed `rosctl` gates (blockers stop the pipeline).
- **H** controls are mandatory human checks: `rosctl approve` will not record an approval until the owner confirms each item for that stage.
- **Residual risk** is what remains *after* the controls, judged honestly. No control makes a risk zero.

Enforcement: fail-closed gate: 58, fail-closed gate + human gate: 57, mandatory human gate: 21. Residual risk: high: 30, low: 35, medium: 71.

| # | Category | Error | Controls | Enforcement | Residual |
|---|---|---|---|---|---|
| 1 | Literature | Fully fabricated reference | C01, C07 | fail-closed gate | low |
| 2 | Literature | Chimera citation (real DOI, other paper) | C02, C03 | fail-closed gate | low |
| 3 | Literature | Wrong metadata (year, authors, volume, pages) | C03 | fail-closed gate | medium |
| 4 | Literature | Real citation that does not support the claim | C08, C07, H05, H10 | fail-closed gate + human gate | high |
| 5 | Literature | Overstating a paper's findings | C11, H11 | fail-closed gate + human gate | high |
| 6 | Literature | Retracted paper used as valid source | C04 | fail-closed gate | medium |
| 7 | Literature | Summarising a whole paper from its abstract | C08, H01, H05 | fail-closed gate + human gate | medium |
| 8 | Literature | Pretending to have read the PDF | C08 | fail-closed gate | low |
| 9 | Literature | Misreading PDF tables/figures | C39, H10 | fail-closed gate + human gate | medium |
| 10 | Literature | Fabricated quotations and page numbers | C08 | fail-closed gate | low |
| 11 | Literature | Secondary citation presented as primary | H05, H10 | mandatory human gate | medium |
| 12 | Literature | False consensus | C09 | fail-closed gate | medium |
| 13 | Literature | Outdated information presented as current | C16, H02 | fail-closed gate + human gate | medium |
| 14 | Literature | Preprint presented as peer-reviewed | C05 | fail-closed gate | low |
| 15 | Literature | One-sided literature (English/western/open access only) | C18, H03 | fail-closed gate + human gate | medium |
| 16 | Literature | Broken DOIs and URLs | C01, C06 | fail-closed gate | low |
| 17 | Novelty | 'No previous research' claims | C10, C17, C20, H02 | fail-closed gate + human gate | medium |
| 18 | Novelty | False research gap | C17, C20, H02 | fail-closed gate + human gate | medium |
| 19 | Novelty | Old method under a new name | C16, H02 | fail-closed gate + human gate | high |
| 20 | Novelty | Overstated importance and feasibility | C15, H04 | fail-closed gate + human gate | medium |
| 21 | Novelty | Sycophancy | C22, H04 | fail-closed gate + human gate | high |
| 22 | Design | Untestable or vague hypothesis | C21, C23 | fail-closed gate | low |
| 23 | Design | Design does not match the question | C24, H06 | fail-closed gate + human gate | medium |
| 24 | Design | Pseudoreplication | C24, H07 | fail-closed gate + human gate | medium |
| 25 | Design | Blocking and design-structure errors | C24, H07 | fail-closed gate + human gate | medium |
| 26 | Design | Fabricated or wrong sample size / power | C24, C39, H08 | fail-closed gate + human gate | medium |
| 27 | Design | Missing controls or confounders | C24, H06 | fail-closed gate + human gate | medium |
| 28 | Design | Fabricated protocol values | C39, H08 | fail-closed gate + human gate | medium |
| 29 | Design | Fabricated local facts | C39, H08 | fail-closed gate + human gate | medium |
| 30 | Design | Assuming equipment/software availability | H04 | mandatory human gate | medium |
| 31 | Dataset | Fabricating data | C31, C30, C25 | fail-closed gate | low |
| 32 | Dataset | Non-existent dataset | C25, C26 | fail-closed gate | low |
| 33 | Dataset | Misread units or codebook | C27 | fail-closed gate | medium |
| 34 | Dataset | Silent data cleaning | C58, H13 | fail-closed gate + human gate | medium |
| 35 | Dataset | Data leakage | C36, C24 | fail-closed gate | medium |
| 36 | Dataset | Assuming representativeness | H11 | mandatory human gate | high |
| 37 | Dataset | Ignoring license and privacy | C26, C28, H22 | fail-closed gate + human gate | medium |
| 38 | Statistics | Mental arithmetic instead of code | C39, C29 | fail-closed gate | low |
| 39 | Statistics | Text numbers differ from code output | C39 | fail-closed gate | low |
| 40 | Statistics | Unchecked test assumptions | C24, H09 | fail-closed gate + human gate | medium |
| 41 | Statistics | p-value misinterpretation | C11 | fail-closed gate | medium |
| 42 | Statistics | No multiple-comparison correction | C24, C23, H09 | fail-closed gate + human gate | medium |
| 43 | Statistics | Wrong post-hoc test | C24, H09 | fail-closed gate + human gate | medium |
| 44 | Statistics | SD/SE/CI confusion | C12, C45 | fail-closed gate | medium |
| 45 | Statistics | Ignoring interactions | C24, H09 | fail-closed gate + human gate | medium |
| 46 | Statistics | Inconsistent df, statistic and p-value | C38 | fail-closed gate | low |
| 47 | Statistics | Training-set R2/accuracy reported as performance | C40, C36 | fail-closed gate | medium |
| 48 | Statistics | Correlation reported as causation | C24, H11 | fail-closed gate + human gate | high |
| 49 | ML | Fabricating results when code fails | C29, C30, C55 | fail-closed gate | low |
| 50 | ML | Claiming to have run code | C29, C30 | fail-closed gate | low |
| 51 | ML | Silent bugs in running code | C37, C29, C35 | fail-closed gate | medium |
| 52 | ML | Non-existent or deprecated APIs | C29, C55 | fail-closed gate | low |
| 53 | ML | Weak or unfair baselines | C24, C46 | fail-closed gate | medium |
| 54 | ML | Single-seed results | C24 | fail-closed gate | medium |
| 55 | ML | Wrong metric (accuracy on imbalanced data) | C24 | fail-closed gate | medium |
| 56 | ML | Hyperparameter tuning on the test set | C24, C36 | fail-closed gate | medium |
| 57 | ML | Not reproducible (no pins, seeds, environment) | C33, C25, C29 | fail-closed gate | low |
| 58 | Interpretation | Over-generalisation | H11 | mandatory human gate | high |
| 59 | Interpretation | Untested mechanism as explanation | H11 | mandatory human gate | high |
| 60 | Interpretation | Hiding or spinning negative results | C41, C59, C11, H16 | fail-closed gate + human gate | medium |
| 61 | Interpretation | Downplayed limitations | C42, H16 | fail-closed gate + human gate | medium |
| 62 | Interpretation | Recommendations bigger than the data | H11 | mandatory human gate | high |
| 63 | Interpretation | Changing position under pressure | C23, H21 | fail-closed gate + human gate | medium |
| 64 | Manuscript | Claims without citation | C09, C07, H10 | fail-closed gate + human gate | high |
| 65 | Manuscript | Internal inconsistency (abstract vs results) | C39 | fail-closed gate | medium |
| 66 | Manuscript | Figure/table/text mismatch | C45, H12 | fail-closed gate + human gate | medium |
| 67 | Manuscript | Methods describe work not done | C59, H13, C29 | fail-closed gate + human gate | medium |
| 68 | Manuscript | Fabricated administrative statements | C44, H22 | fail-closed gate + human gate | medium |
| 69 | Manuscript | Subtle terminology errors | H15 | mandatory human gate | high |
| 70 | Manuscript | Bangla-English mistranslation of terms | H15 | mandatory human gate | high |
| 71 | Manuscript | Close paraphrase / tortured phrases | C14, H24 | fail-closed gate + human gate | medium |
| 72 | Manuscript | Fabricated journal guidelines | C51, H23 | fail-closed gate + human gate | low |
| 73 | Submission | Fabricated journal facts | C50, H23 | fail-closed gate + human gate | low |
| 74 | Submission | Recommending predatory journals | C50, H23 | fail-closed gate + human gate | low |
| 75 | Submission | Wrong AI-disclosure policy | C43, H23 | fail-closed gate + human gate | low |
| 76 | Agent | Claiming everything was verified | C57 | fail-closed gate | low |
| 77 | Agent | Self-evaluating own work as excellent | C46, C47 | fail-closed gate | medium |
| 78 | Agent | Not separating assumption from fact | C44, H11 | fail-closed gate + human gate | high |
| 79 | Agent | Forgetting earlier decisions in long sessions | C23, C57 | fail-closed gate | medium |
| 80 | Agent | Silently changing scope or method | C23, C41, C59 | fail-closed gate | low |
| 81 | Agent | Fabricated or misreported tool output | C19 | fail-closed gate | medium |
| 82 | Agent | Pretending to follow the rules | C57, C53 | fail-closed gate | low |
| 83 | Reasoning | Accepting a false premise | C22 | fail-closed gate | medium |
| 84 | Reasoning | Answer steered by the prompt | C22, H04 | fail-closed gate + human gate | high |
| 85 | Reasoning | Anchoring on first sources | C16, C17 | fail-closed gate | medium |
| 86 | Reasoning | Stopping search once support is found | C17, C20 | fail-closed gate | medium |
| 87 | Reasoning | Inventing a middle ground between contradictions | H14 | mandatory human gate | high |
| 88 | Reasoning | Citation count taken as correctness | H14 | mandatory human gate | high |
| 89 | Reasoning | Verification with the same model | C47, H20 | fail-closed gate + human gate | medium |
| 90 | Synthesis | Keywords decide what is found | C16, H03 | fail-closed gate + human gate | medium |
| 91 | Synthesis | Amplified publication bias | H14 | mandatory human gate | high |
| 92 | Synthesis | Winner's curse | H14 | mandatory human gate | high |
| 93 | Synthesis | Double counting the same data | H14 | mandatory human gate | high |
| 94 | Synthesis | Averaging heterogeneous studies | H14 | mandatory human gate | high |
| 95 | Synthesis | Applying results out of context | H14, H11 | mandatory human gate | high |
| 96 | Synthesis | Hedges lost through repeated summarising | C08, H14 | fail-closed gate + human gate | high |
| 97 | Synthesis | Ignoring the middle of long documents | C08, H01 | fail-closed gate + human gate | high |
| 98 | Synthesis | Treating truncated input as complete | C08, H01 | fail-closed gate + human gate | medium |
| 99 | Agent behaviour | Modifying evaluation code or thresholds | C35, C23, C54 | fail-closed gate | medium |
| 100 | Agent behaviour | Fallback to fake data when files are missing | C31 | fail-closed gate | low |
| 101 | Agent behaviour | Swallowing errors | C31 | fail-closed gate | low |
| 102 | Agent behaviour | Reading stale outputs | C30 | fail-closed gate | low |
| 103 | Agent behaviour | Hidden analysis branches (forking paths) | C29, C23, C59, H17 | fail-closed gate + human gate | medium |
| 104 | Agent behaviour | Overwriting raw data | C25, C54 | fail-closed gate | low |
| 105 | Agent behaviour | Installing hallucinated packages (slopsquatting) | C34, C54 | fail-closed gate | low |
| 106 | Agent behaviour | Excessive permissions | C54, C53 | fail-closed gate | medium |
| 107 | Agent behaviour | Prompt injection | C49 | fail-closed gate | medium |
| 108 | Agent behaviour | AI itself not reproducible | C43, H19 | fail-closed gate + human gate | medium |
| 109 | Agent behaviour | Benchmark memorisation | C24, H18 | fail-closed gate + human gate | high |
| 110 | Data format | Agriculture-specific unit errors | C27 | fail-closed gate | medium |
| 111 | Data format | Number and date format errors | C27 | fail-closed gate | low |
| 112 | Data format | Spreadsheet auto-conversion | C27 | fail-closed gate | low |
| 113 | Data format | False precision / premature rounding | C13 | fail-closed gate | low |
| 114 | Data format | Bioinformatics version confusion | C24, H18 | fail-closed gate + human gate | medium |
| 115 | Statistics traps | Numeric-coded treatments treated as continuous | C32, C27 | fail-closed gate | medium |
| 116 | Statistics traps | Software default sum-of-squares type | C24 | fail-closed gate | low |
| 117 | Statistics traps | Fixed vs random effects misassigned | C24, H09 | fail-closed gate + human gate | medium |
| 118 | Statistics traps | Transformation errors | C24 | fail-closed gate | medium |
| 119 | Statistics traps | Ignoring temporal/spatial dependence | C24, C36 | fail-closed gate | medium |
| 120 | Statistics traps | Regression to the mean, survivorship, ecological fallacy | H11 | mandatory human gate | high |
| 121 | Statistics traps | Survey analysis errors | C24, H18 | fail-closed gate + human gate | medium |
| 122 | Statistics traps | Fabricated qualitative themes and quotes | C48 | fail-closed gate | low |
| 123 | Domain | GitHub mining without bot/fork/duplicate filtering | C24, H18 | fail-closed gate + human gate | medium |
| 124 | Domain | Claiming ethics approval is not needed | C24, C28, H22 | fail-closed gate + human gate | medium |
| 125 | Domain | Subtle equation errors | H15 | mandatory human gate | high |
| 126 | Domain | Misleading figures | C45, H12 | fail-closed gate + human gate | medium |
| 127 | Publication | False claims in the rebuttal | C52 | fail-closed gate | low |
| 128 | Publication | Manuscript and analysis versions differ | C30, C39 | fail-closed gate | low |
| 129 | Publication | Supplement differs from main text | C39, H12 | fail-closed gate + human gate | medium |
| 130 | Publication | Leaking confidential material to AI | H25 | mandatory human gate | high |
| 131 | Publication | Copyright infringement | C45, H24 | fail-closed gate + human gate | medium |
| 132 | Human | Fluency mistaken for quality | H21, H10 | mandatory human gate | high |
| 133 | Human | Automation bias | C56, H10 | fail-closed gate + human gate | medium |
| 134 | Human | Blind trust in checking tools | H26 | mandatory human gate | high |
| 135 | Human | Circular verification (AI checks AI) | C47, H20 | fail-closed gate + human gate | medium |
| 136 | Human | Loss of own expertise | H21 | mandatory human gate | high |

## Control registry

| ID | Kind | Stage | Implementation | What it enforces |
|---|---|---|---|---|
| C01 | auto | S1 | `check_bib` | Every reference resolves at doi.org (registry) or is a reachable URL; ledger required |
| C02 | auto | S1 | `check_bib` | Registered title must match bib title (>= 0.85 similarity) |
| C03 | auto | S1 | `check_bib` | Year (+/-1) and first author must match registry |
| C04 | auto | S1 | `check_bib` | OpenAlex retraction flag blocks |
| C05 | auto | S7 | `check_citations` | Cited preprints must be labelled 'preprint' in the citing sentence |
| C06 | auto | S1 | `check_bib` | URL-only references must be reachable |
| C07 | auto | S7 | `check_citations` | Every citation needs a CLAIM_SUPPORT row |
| C08 | auto | S7 | `check_citations` | Every cited source has saved text with ACCESS header; quotes must occur verbatim |
| C09 | auto | S7 | `check_language` | Consensus wording needs >= 3 citations |
| C10 | auto | S7 | `check_language` | Novelty wording must be hedged |
| C11 | auto | S7 | `check_language` | p-value misinterpretation and significance spin |
| C12 | auto | S7 | `check_language` | '±' must say SD/SE/CI |
| C13 | auto | S7 | `check_language` | No false precision (>= 5 decimals) |
| C14 | auto | S7 | `check_language` | Tortured phrases |
| C15 | auto | S7 | `check_language` | Hype words |
| C16 | auto | S1 | `stage_s1` | >= 10 logged queries over >= 3 sources |
| C17 | auto | S1 | `stage_s1` | >= 1 counter-evidence search logged |
| C18 | auto | S1 | `stage_s1` | Grey/regional literature searched |
| C19 | auto | S1 | `stage_s1` | Each search row keeps its raw tool output; hit counts match |
| C20 | auto | S1 | `stage_s1` | Novelty verdict has contrary-evidence and search-limitation sections |
| C21 | auto | S0 | `lint_proposal` | Proposal lint: falsifiable hypotheses, decision rules, data, validation |
| C22 | auto | S0 | `check_neutral_questions` | Research questions must not presuppose answers |
| C23 | auto | S2 | `stage_s2` | Protocol SHA-256 frozen at S2; changes only as dated deviations |
| C24 | auto | S2 | `check_protocol_requirements` | Method-conditional protocol requirements (24 rules) |
| C25 | auto | S3 | `stage_s3` | Raw data hashed and read-only |
| C26 | auto | S3 | `stage_s3` | Data provenance: URL, license, path |
| C27 | auto | S3 | `check_schema` | Data schema: units, types, ranges, date formats, mangled values |
| C28 | auto | S3 | `check_pii` | Personal data requires an ethics statement |
| C29 | auto | S4 | `stage_s4` | Successful logged runs and passing tests after freeze |
| C30 | auto | S4 | `check_outputs` | Result files must equal the output of a logged run and not be stale |
| C31 | auto | S4 | `check_code` | No synthetic fallbacks, silent excepts or suppressed warnings in analysis code |
| C32 | auto | S4 | `check_factor_formulas` | Numeric-coded categoricals wrapped as factors in formulas |
| C33 | auto | S4 | `check_environment` | Pinned environment lock file |
| C34 | auto | S4 | `check_environment` | Dependencies exist and are >= 90 days old |
| C35 | auto | S4 | `check_test_lock` | Tests/evaluation code locked after S4 |
| C36 | auto | S4 | `check_splits` | Split manifest: no group in train and test |
| C37 | auto | S5 | `check_recompute` | Independent re-computation within tolerance |
| C38 | auto | S7 | `check_stats` | p-values recomputed from statistics |
| C39 | auto | S7 | `check_numbers` | Every number traced to an exact cell |
| C40 | auto | S7 | `check_numbers` | Performance numbers must not come from training data |
| C41 | auto | S7 | `check_manuscript_structure` | Every protocol hypothesis reported |
| C42 | auto | S7 | `check_manuscript_structure` | Limitations section >= 120 words |
| C43 | auto | S7 | `check_ai_log` | AI usage log and declaration consistency |
| C44 | auto | S7 | `check_manuscript_structure` | Required sections, no placeholders or [VERIFY] |
| C45 | auto | S6 | `stage_s6` | Figures script-generated from logged runs, error bars declared |
| C46 | auto | S8 | `check_review` | Four independent reviewer reports, no self-scoring |
| C47 | auto | S8 | `check_review` | At least one reviewer differs from the drafting model |
| C48 | auto | S7 | `check_participant_quotes` | Participant quotes must occur in raw transcripts |
| C49 | auto | S1 | `check_injection` | Prompt-injection scan of sources; human acknowledgement required |
| C50 | auto | S9 | `stage_s9` | Journal verified by owner with source and date |
| C51 | auto | S9 | `stage_s9` | Downloaded guide for authors required |
| C52 | auto | S10 | `stage_s10` | Rebuttal 'Change' quotes must exist in manuscript |
| C53 | auto | S1 | `approval_refusal` | Approvals refused in agent sessions / non-TTY |
| C54 | auto | S0 | `check_claude_settings` | Claude Code project permissions deny protected paths and human-only commands |
| C55 | auto | S4 | `stage_s4` | Last failed run blocks (stop on failure) |
| C56 | auto | S8 | `spot_check_sample` | Random spot-check sample shown at S8 approval |
| C57 | auto | S0 | `run_stage_checks` | Cumulative gates; regression clears later passes |
| C58 | auto | S3 | `check_cleaning_log` | Processed data require a cleaning log (rows in/out, rule, script) |
| C59 | auto | S7 | `check_execution` | Every pre-registered analysis (A#) executed by a logged run or recorded as a deviation; false no-deviation claims blocked |
| H01 | human | S1 | `rosctl approve S1` | I read the three closest papers in full text myself (not only abstracts or AI summaries). |
| H02 | human | S1 | `rosctl approve S1` | Novelty rests on evidence, not on missing search hits; the contrary evidence was examined; the method is not an old one renamed. |
| H03 | human | S1 | `rosctl approve S1` | Regional, grey and non-English sources relevant to the setting (national institutes, theses, reports) were searched. |
| H04 | human | S1 | `rosctl approve S1` | The agent challenged my idea; time, budget, data, equipment and software are realistic. |
| H05 | human | S1 | `rosctl approve S1` | The sources cited in NOVELTY_VERDICT really say what is attributed to them, and they are primary sources. |
| H06 | human | S2 | `rosctl approve S2` | The design matches the question; causal claims only where the design identifies causation; controls and confounders are listed. |
| H07 | human | S2 | `rosctl approve S2` | Experimental unit, replication, blocking and season/location effects are correct (no pseudoreplication). |
| H08 | human | S2 | `rosctl approve S2` | Sample size/power and every protocol constant (doses, rates, varieties, seasons, local units, standards) come from cited official sources. |
| H09 | human | S2 | `rosctl approve S2` | Model choices are right: fixed vs random effects, sum-of-squares type, transformations, assumption checks, post-hoc tests, interactions. |
| H10 | human | S8 | `rosctl approve S8` | I verified the randomly sampled numbers against the results files and the sampled claims against the source passages. |
| H11 | human | S8 | `rosctl approve S8` | No overstatement: no may->does, lab->field, correlation->causation, untested mechanisms, or generalisation beyond sites, seasons and populations. |
| H12 | human | S8 | `rosctl approve S8` | Figures, tables, captions and supplement agree with the text; axes are not misleading; error bars are defined. |
| H13 | human | S8 | `rosctl approve S8` | Methods describe only what was actually done (checked against RUN_LOG, scripts and the cleaning log). |
| H14 | human | S8 | `rosctl approve S8` | Synthesis is honest: contradictions reported not averaged away; publication bias, small-study effects, double-counted trials, heterogeneity, context transfer and hedges handled. |
| H15 | human | S8 | `rosctl approve S8` | Terminology, Bangla<->English translations, equations and notation are correct and consistent. |
| H16 | human | S8 | `rosctl approve S8` | Negative and contrary results are reported; limitations are specific and not spun. |
| H17 | human | S8 | `rosctl approve S8` | All analysis runs, including exploratory and failed ones, are disclosed (no garden of forking paths). |
| H18 | human | S8 | `rosctl approve S8` | Benchmark contamination and domain pitfalls (genome versions, repository-mining filters, survey validity, qualitative coding) are addressed. |
| H19 | human | S8 | `rosctl approve S8` | The AI usage log (models, versions, dates, prompts) is complete enough to reproduce the AI-assisted steps. |
| H20 | human | S8 | `rosctl approve S8` | At least one reviewer was a human or a different model family; AI output was not verified only by the same AI. |
| H21 | human | S8 | `rosctl approve S8` | I can explain and defend every analysis and claim myself, without the AI. |
| H22 | human | S9 | `rosctl approve S9` | Ethics approval, consent, funding, acknowledgements, author contributions and data-availability statements are true and documented. |
| H23 | human | S9 | `rosctl approve S9` | Journal facts (scope, indexing, quartile, APC, AI policy, author guidelines) were verified on official sites; the journal is not predatory. |
| H24 | human | S9 | `rosctl approve S9` | An institutional similarity check was run; there is no close paraphrase; third-party figures/tables have permission. |
| H25 | human | S9 | `rosctl approve S9` | No confidential or unpublished data or manuscripts were given to AI services that the applicable policies forbid. |
| H26 | human | S9 | `rosctl approve S9` | Automated checker outputs were reviewed for false positives/negatives instead of being trusted blindly. |
