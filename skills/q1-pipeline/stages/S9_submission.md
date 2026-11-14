# S9: Submission package (prepared by the agent, submitted by the owner)

## Steps

1. **Journal verification.** For the chosen journal, fill `submission/JOURNAL_CHECK.csv`: publisher,
   ISSN, quartile, `quartile_source` (e.g. SJR <year>, JCR <year>), `checked_date`, scope fit,
   APC / subscription route, AI-policy URL. Quartiles change yearly and differ by category: the owner
   must verify on scimagojr.com / JCR and set `owner_verified=yes`. Check "Think. Check. Submit." to
   avoid predatory journals.
2. **Format** to the current Guide for Authors (the owner downloads it): structure, limits, reference
   style, highlights, graphical abstract, statements. Use journal templates (K-Dense `venue-templates`
   if installed).
3. **Cover letter** (`submission/COVER_LETTER.md`): the problem, the contribution in 2–3 sentences, why
   this journal (cite 1–2 recent papers from it), confirmation of originality and no concurrent
   submission, data/code availability, AI-use declaration, suggested reviewers (only cited authors,
   no conflicts, the owner decides).
4. **Reproducibility archive:** code, lock file, processed data (if license allows), `README`,
   `CITATION.cff`, license; zipped and ready for Zenodo (the owner uploads and inserts the DOI).
5. **Preprint** (optional, owner decides; check journal policy first).
6. Tick `submission/SUBMISSION_CHECKLIST.md` only with evidence. Owner runs the institutional similarity
   check (Turnitin/iThenticate).
7. `rosctl gate S9`.

## Human gate

The owner reviews everything, runs `rosctl approve S9`, and **submits personally**. The agent never
submits, never creates journal accounts, never emails editors.
