# S1: Literature, positioning and novelty

**Goal:** know the field well enough that no reviewer can name a paper we missed, and prove (with
evidence) what is new. This stage decides whether the project should continue.

## Steps

1. **Search protocol first.** Write `literature/SEARCH_PROTOCOL.md` BEFORE searching:
   databases/sources, exact query strings (concept blocks with synonyms, joined with AND/OR), date range,
   languages, inclusion/exclusion criteria, screening procedure, and the stopping rule (e.g. "stop when
   two consecutive snowball rounds add < 2 relevant papers"). Use the domain pack's search vocabulary
   (`.ros/domain/DOMAIN.md` → "Search vocabulary").
2. **Search broadly, log everything.** Use the `q1-literature` skill (paper-search CLI/MCP over
   OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed, CORE, DOAJ ...). Every query → one row in
   `ledgers/SEARCH_LOG.csv` (date, source, query, filters, hits, screened, included). Minimum 10
   queries over 3 sources; a Q1 review usually needs far more.
3. **Snowball.** For the 3–5 most relevant papers, collect forward citations and backward references
   (OpenAlex; see `q1-literature`). Log each round.
4. **Screen** titles/abstracts against the criteria. Download only legal open-access PDFs into
   `literature/pdfs/`.
5. **Closest work table.** Fill `literature/CLOSEST_WORK.csv` with the ≥10 closest works: what they did,
   data, method, key result, limitation, `overlap_with_us` (`none|partial|direct`), and
   `evidence_location` (page/section you actually read).
6. **Verify every reference.** For each work: resolve the DOI (Crossref/OpenAlex), get BibTeX from
   `https://doi.org/<DOI>` with `Accept: application/x-bibtex`, add it to `refs/refs.bib` with a
   consistent citekey (e.g. `smith2023yield`). No DOI → use the stable URL. Never type BibTeX from memory.
7. **Adversarial novelty check.** Ask, and answer with evidence:
   - "What paper would a hostile reviewer cite to say this is not new?"
   - Has the same question been answered with different data? The same data with a different method?
   - Is there a recent preprint (last 12 months) doing this?
   If PaperQA2 is available and the owner allowed LLM calls, ask it the novelty questions over
   `literature/pdfs/` (see `q1-literature`). PaperQA2 answers are leads, not proof: open the cited passage.
8. **Novelty verdict.** Write `literature/NOVELTY_VERDICT.md` (≥150 words): the gap statement, the
   evidence for it (citekeys + locations), the closest competitors and how we differ on question / data /
   method / result, residual risk, and a recommendation: **proceed / reframe / stop**.
9. Run `rosctl gate S1`. It will pass the checks and then wait for the owner.

## Human gate

Stop. Present: the verdict, the 3 closest works side by side, every `direct` overlap, and the
recommendation. The owner reads the key papers and runs `rosctl approve S1` (or asks you to reframe).

## Failure modes

- Searching only one database or only recent years.
- Citing a paper for a claim after reading only its title.
- Declaring novelty because the exact keyword combination returned nothing.
- Hiding an overlapping paper.
