# S3: Data acquisition and provenance

**Goal:** every byte of input data is legally obtained, documented, hashed and read-only, so anyone can
reproduce the study and nobody (including you) can silently change the inputs.

## Steps

0. **Discovery (only if the protocol's datasets are insufficient or unavailable).** Search, in order:
   `.ros/domain/DATASETS.md`; official portals named there; research-data repositories with open
   APIs (Zenodo `https://zenodo.org/api/records?q=...`, Harvard Dataverse
   `https://dataverse.harvard.edu/api/search?q=...`, Figshare, Dryad, PANGAEA); and "data papers" in
   journals such as Scientific Data or Earth System Science Data (via `q1-literature`). For each
   candidate record: coverage, unit, license, size, version, and whether independent validation data
   exist. Write candidates to `ledgers/DECISION_LOG.csv`; adding or replacing a dataset needs the
   owner's approval (PROPOSAL §12) and a `## Deviations` entry.
1. For each dataset in the protocol, write a download script in `analysis/` (e.g.
   `analysis/00_get_<dataset>.py`). Prefer official APIs and documented bulk endpoints. Respect rate
   limits and terms of use. Never scrape publisher or login-protected sites.
2. Run each with `rosctl run -- python analysis/00_get_<dataset>.py`. Save into `data/raw/<dataset_id>/`.
   If a download fails, STOP and report: do not substitute another dataset without owner approval.
3. Check the size limit in `PROPOSAL.md` §11 before large downloads; ask if it would be exceeded.
4. Hash: `rosctl hash data/raw/<dataset_id>` and copy the rows into `ledgers/DATA_PROVENANCE.csv`
   (one row per file, or per archive), with source URL, version/access date and license.
5. Make raw data read-only on disk (`chmod -R a-w data/raw/<dataset_id>`).
6. Write `data/DATA_CARD.md`: coverage, units, variables, known issues, license, leakage risks.
7. **Data sanity report** (exploratory, not confirmatory): `analysis/01_data_audit.py` writes
   `results/data_audit/` (row counts, missingness, ranges, duplicates, outliers, unit checks,
   spatial/temporal coverage maps). Look for impossible values (negative yields, rainfall > records,
   dates out of season). Record issues in DATA_CARD.
8. `rosctl gate S3`.

## Failure modes

- Manually downloaded files with no script and no access date.
- Editing a raw CSV "to fix a typo" (do it in processing code instead).
- Ignoring licenses that forbid redistribution (then share code + access steps, not the data).
