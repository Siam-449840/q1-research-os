#!/usr/bin/env python3
"""Citation Snowballing via the Free OpenAlex REST API (Stdlib-Only).

Retrieves forward citations (papers citing a target work) and backward
references (`referenced_works` of a target work) using OpenAlex's free API:
- Citing papers: https://api.openalex.org/works?filter=cites:<OPENALEX_WORK_ID>&per-page=50
- Referenced papers: field `referenced_works` of https://api.openalex.org/works/doi:<DOI>

Logs every query (with timestamp, endpoint URL, status, and result count) to a
CSV audit file and saves discovered works to an output CSV file.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OPENALEX_BASE_URL = "https://api.openalex.org/works"
OPENALEX_BATCH_SIZE = 50
# Optional: export OPENALEX_MAILTO=you@example.org to use OpenAlex's faster polite pool.
_MAILTO = os.environ.get("OPENALEX_MAILTO", "").strip()
USER_AGENT = "Q1ResearchOS/1.0 (+https://github.com/Siam-449840/q1-research-os)" + (
    f" mailto:{_MAILTO}" if _MAILTO else ""
)


@dataclass(frozen=True)
class SnowballConfig:
    """Immutable configuration for OpenAlex citation snowballing."""

    doi: Optional[str]
    openalex_id: Optional[str]
    direction: str
    per_page: int
    output_csv: Path
    log_csv: Path
    dry_run: bool


def _append_query_log(
    log_csv: Path,
    identifier: str,
    direction: str,
    url: str,
    status: str,
    count: int,
) -> None:
    """Append a single query audit record to the query log CSV."""
    log_csv.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_csv.exists()
    with log_csv.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if not file_exists:
            writer.writerow(
                [
                    "timestamp_utc",
                    "input_identifier",
                    "direction",
                    "request_url",
                    "status",
                    "result_count",
                ]
            )
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                identifier,
                direction,
                url,
                status,
                count,
            ]
        )


def _fetch_json(url: str, log_http_error: bool = True) -> Dict[str, Any]:
    """Perform a GET request to OpenAlex using Python stdlib urllib."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if log_http_error:
            logger.error("HTTP error %s when fetching %s", exc.code, url)
        raise
    except urllib.error.URLError as exc:
        logger.error("Network error when fetching %s: %s", url, exc.reason)
        raise


def _normalize_work_id(raw_id: str) -> str:
    """Extract short OpenAlex work ID (e.g. W2741809807) from URL or string."""
    cleaned = raw_id.strip().rstrip("/")
    if "/" in cleaned:
        cleaned = cleaned.split("/")[-1]
    return cleaned


def _fetch_referenced_works_metadata(
    referenced_ids: List[str],
    identifier: str,
    log_csv: Path,
) -> Dict[str, Dict[str, Any]]:
    """Batch-fetch metadata for referenced OpenAlex work IDs (50 per request)."""
    metadata_by_id: Dict[str, Dict[str, Any]] = {}
    for start in range(0, len(referenced_ids), OPENALEX_BATCH_SIZE):
        batch_ids = referenced_ids[start : start + OPENALEX_BATCH_SIZE]
        filter_expr = "|".join(batch_ids)
        batch_url = (
            f"{OPENALEX_BASE_URL}?filter=openalex_id:{filter_expr}"
            f"&per-page={OPENALEX_BATCH_SIZE}"
        )
        batch_data = _fetch_json(batch_url)
        results = batch_data.get("results", []) or []
        _append_query_log(
            log_csv,
            identifier,
            "references_batch",
            batch_url,
            "OK",
            len(results),
        )
        for item in results:
            short_id = _normalize_work_id(item.get("id", ""))
            if short_id:
                metadata_by_id[short_id] = item

    for ref_id in referenced_ids:
        item = metadata_by_id.get(ref_id)
        if not item:
            single_url = f"{OPENALEX_BASE_URL}/{ref_id}"
            try:
                single_item = _fetch_json(single_url, log_http_error=False)
                _append_query_log(
                    log_csv,
                    identifier,
                    "reference_single",
                    single_url,
                    "OK",
                    1,
                )
                metadata_by_id[ref_id] = single_item
            except urllib.error.HTTPError as exc:
                logger.warning(
                    "Referenced work %s returned HTTP %s on direct lookup",
                    ref_id,
                    exc.code,
                )
                _append_query_log(
                    log_csv,
                    identifier,
                    "reference_single",
                    single_url,
                    f"HTTP_{exc.code}",
                    0,
                )
                metadata_by_id[ref_id] = {
                    "id": ref_id,
                    "title": f"[OpenAlex HTTP {exc.code}: {ref_id}]",
                }
    return metadata_by_id


def run_snowball(cfg: SnowballConfig) -> List[Dict[str, Any]]:
    """Execute forward and/or backward citation snowballing against OpenAlex."""
    identifier = cfg.doi or cfg.openalex_id or ""
    if cfg.doi:
        clean_doi = cfg.doi.strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if clean_doi.lower().startswith(prefix):
                clean_doi = clean_doi[len(prefix) :]
        work_url = f"{OPENALEX_BASE_URL}/doi:{urllib.parse.quote(clean_doi, safe='/:')}"
    else:
        short_id = _normalize_work_id(cfg.openalex_id or "")
        work_url = f"{OPENALEX_BASE_URL}/{short_id}"

    records: List[Dict[str, Any]] = []

    if cfg.dry_run:
        work_id_placeholder = _normalize_work_id(cfg.openalex_id or "<OPENALEX_WORK_ID>")
        citing_url = (
            f"{OPENALEX_BASE_URL}?filter=cites:{work_id_placeholder}"
            f"&per-page={cfg.per_page}"
        )
        refs_batch_url = (
            f"{OPENALEX_BASE_URL}?filter=openalex_id:W1|W2|..."
            f"&per-page={OPENALEX_BATCH_SIZE}"
        )
        logger.info("[DRY-RUN] Metadata/References endpoint: %s", work_url)
        logger.info("[DRY-RUN] Referenced batch endpoint:    %s", refs_batch_url)
        logger.info("[DRY-RUN] Citing papers endpoint:       %s", citing_url)
        _append_query_log(
            cfg.log_csv, identifier, cfg.direction, work_url, "DRY_RUN", 0
        )
        return records

    work_data = _fetch_json(work_url)
    openalex_work_id = _normalize_work_id(work_data.get("id", ""))
    referenced_urls: List[str] = work_data.get("referenced_works", []) or []
    _append_query_log(
        cfg.log_csv,
        identifier,
        "work_lookup",
        work_url,
        "OK",
        len(referenced_urls),
    )

    if cfg.direction in ("references", "both") and referenced_urls:
        referenced_ids = [_normalize_work_id(ref_url) for ref_url in referenced_urls]
        ref_metadata = _fetch_referenced_works_metadata(
            referenced_ids, identifier, cfg.log_csv
        )
        for ref_id in referenced_ids:
            item = ref_metadata.get(ref_id, {})
            records.append(
                {
                    "direction": "referenced_by_seed",
                    "seed_identifier": identifier,
                    "seed_openalex_id": openalex_work_id,
                    "work_openalex_id": ref_id,
                    "doi": item.get("doi") or "",
                    "title": item.get("title") or item.get("display_name") or "",
                    "publication_year": item.get("publication_year") or "",
                    "cited_by_count": item.get("cited_by_count")
                    if item.get("cited_by_count") is not None
                    else "",
                }
            )

    if cfg.direction in ("citing", "both") and openalex_work_id:
        citing_url = (
            f"{OPENALEX_BASE_URL}?filter=cites:{openalex_work_id}"
            f"&per-page={cfg.per_page}"
        )
        citing_data = _fetch_json(citing_url)
        results = citing_data.get("results", []) or []
        _append_query_log(
            cfg.log_csv,
            identifier,
            "citing",
            citing_url,
            "OK",
            len(results),
        )
        for item in results:
            records.append(
                {
                    "direction": "cites_seed",
                    "seed_identifier": identifier,
                    "seed_openalex_id": openalex_work_id,
                    "work_openalex_id": _normalize_work_id(item.get("id", "")),
                    "doi": item.get("doi") or "",
                    "title": item.get("title") or item.get("display_name") or "",
                    "publication_year": item.get("publication_year") or "",
                    "cited_by_count": item.get("cited_by_count")
                    if item.get("cited_by_count") is not None
                    else 0,
                }
            )

    for idx, row in enumerate(records):
        assert str(row.get("title", "")).strip(), (
            f"Row {idx} (work_openalex_id={row.get('work_openalex_id')}, "
            f"direction={row.get('direction')}) has an empty title"
        )

    cfg.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "direction",
        "seed_identifier",
        "seed_openalex_id",
        "work_openalex_id",
        "doi",
        "title",
        "publication_year",
        "cited_by_count",
    ]
    with cfg.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info("Saved %d snowball records to %s", len(records), cfg.output_csv)
    return records


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Citation Snowballing via Free OpenAlex API (stdlib-only). "
            "Queries works?filter=cites:<OPENALEX_WORK_ID>&per-page=50 for citing "
            "papers and referenced_works from works/doi:<DOI> for references."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doi", type=str, help="Seed paper DOI (e.g. 10.1038/nature12373)")
    group.add_argument(
        "--openalex-id",
        type=str,
        help="Seed OpenAlex Work ID (e.g. W2741809807)",
    )
    parser.add_argument(
        "--direction",
        choices=("both", "citing", "references"),
        default="both",
        help="Snowballing direction: citing, references, or both (default: both)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=50,
        help="Number of citing papers to fetch per page (default: 50, max: 200)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("literature/snowball/snowball_results.csv"),
        help="Output CSV path for discovered works",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("literature/snowball/snowball_query_log.csv"),
        help="Audit log CSV path recording every query",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print and log the OpenAlex endpoint URLs without making network requests",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    output_csv: Path = args.output
    log_csv: Path = args.log_file
    cfg = SnowballConfig(
        doi=args.doi,
        openalex_id=args.openalex_id,
        direction=args.direction,
        per_page=args.per_page,
        output_csv=output_csv,
        log_csv=log_csv,
        dry_run=args.dry_run,
    )
    run_snowball(cfg)


if __name__ == "__main__":
    main()
