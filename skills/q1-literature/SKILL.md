---
name: q1-literature
description: Systematic, logged, legal literature search and reference verification for Q1 Research OS - paper-search CLI/MCP (OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed, CORE, DOAJ...), OpenAlex citation snowballing, open-access PDF download, PaperQA2 question answering over PDFs, Zotero, and DOI-verified BibTeX. Use in S1 (novelty), S7 (citations) and S8 (adversarial evidence).
---

# Literature toolkit

Every action here must leave a trace: queries → `ledgers/SEARCH_LOG.csv`, references →
`refs/refs.bib` (with DOI/URL), claims → `ledgers/CLAIM_SUPPORT.csv`.

## 1. Search (paper-search-mcp)

```bash
paper-search search "<query>" -n 20 -s openalex,crossref,semantic,arxiv -y 2015-2026
paper-search search "<query>" -n 20 -s pubmed,europepmc        # life-science topics
paper-search search "<query>" -n 20 -s core,doaj               # open-access coverage
paper-search download <source> <paper_id> -o literature/pdfs   # open access only
paper-search read <source> <paper_id>                          # extract text
```

- Not installed? `uv tool install paper-search-mcp`. Or use the `paper-search` MCP server if configured.
- Never enable Sci-Hub or any bypass option, even if the tool offers it.
- Build queries from concept blocks: `(population/system) AND (intervention/method) AND (outcome)`,
  each block with synonyms from `.ros/domain/DOMAIN.md` → "Search vocabulary".
- Log each query immediately (one row per source) in `ledgers/SEARCH_LOG.csv`.

## 2. Citation snowballing (free OpenAlex API, stdlib script)

```bash
python3 .claude/skills/q1-literature/scripts/snowball_openalex.py --doi <DOI> --direction both
# Antigravity path: .agents/skills/q1-literature/scripts/snowball_openalex.py
# --dry-run prints the endpoints without network calls
```

Outputs `literature/snowball/snowball_results.csv` and an audit log. Screen results; add relevant ones.

## 3. Verify and record a reference

1. Resolve: `https://api.crossref.org/works/<DOI>` (or OpenAlex `https://api.openalex.org/works/doi:<DOI>`).
   Confirm title, authors, year, venue match what you think it is. Check for retraction notices.
2. BibTeX: `curl -sL -H "Accept: application/x-bibtex" https://doi.org/<DOI>` → append to `refs/refs.bib`.
   Normalise the citekey (`firstauthorYEARkeyword`). Never write BibTeX from memory.
3. Before citing for a specific claim: read the passage (open-access full text, or abstract if that is
   all that is legally available, and say so) and add a `ledgers/CLAIM_SUPPORT.csv` row.
4. Batch checks: `bibvet refs/refs.bib` (metadata) and
   `academic-refchecker --paper manuscript/manuscript.md` (existence/hallucination audit). Install:
   `uv tool install academic-refchecker`; `uv tool install git+https://github.com/dipta007/bibvet`.
   Run `<tool> --help` first and use only the flags it prints.

## 4. PaperQA2 over your PDFs (optional; needs an LLM API key)

Ask the owner before the first live call (it costs tokens, even on free tiers there are quotas).

```bash
pqa --agent.index.paper_directory literature/pdfs \
    --llm gemini/<MODEL> --summary_llm gemini/<MODEL> --agent.agent_llm gemini/<MODEL> \
    --embedding gemini/<EMBED_MODEL> \
    ask "Has <method> been used to <task> in <setting>? Cite passages."
# replace `ask "..."` with `view` to check flag parsing without any API call
```

Good questions: "Which studies contradict <claim>?", "What validation designs were used for <task>
and what were their limitations?", "What is the strongest reported baseline for <task> on <data>?".
Treat answers as leads: open each cited passage before relying on it.

## 5. Zotero (optional)

If the owner uses Zotero: Zotero 7 desktop running with the local API enabled, plus `zotero-mcp`
(`uv tool install zotero-mcp-server`). Use it to file papers into a project collection and export
`refs/refs.bib` (Better BibTeX keeps citekeys stable). Zotero is a convenience; `refs/refs.bib` is
what `rosctl` checks.

## 6. Search-quality checklist (S1)

- ≥ 3 sources, ≥ 10 queries, synonyms per concept, date range justified.
- Forward + backward snowballing on the 3–5 closest papers.
- Searched for recent preprints (arXiv, bioRxiv/medRxiv, Research Square, SSRN as relevant).
- Searched for reviews and meta-analyses on the topic.
- Searched non-English or regional sources if the setting demands it.
- Stopping rule met and written down.
