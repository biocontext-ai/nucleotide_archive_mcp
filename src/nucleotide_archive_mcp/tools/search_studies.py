"""Tool for searching RNA-seq studies in ENA."""

from collections import defaultdict
from typing import Annotated, Literal

import httpx
from pydantic import Field

from nucleotide_archive_mcp.config import (
    DEFAULT_ORGANISM,
    DEFAULT_TIMEOUT,
    ENA_BROWSER_API_BASE,
    LibrarySource,
    LibraryStrategy,
)
from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp
from nucleotide_archive_mcp.utils import build_technology_filter, normalize_organism

MAX_STUDY_RESULTS = 60
MAX_RUN_ROWS = 200_000

TechnologyPreset = Literal["bulk", "single-cell", "small-rna", "ribo-seq", "rna-all"]


def _sanitize_term(value: str) -> str:
    return value.replace('"', "").strip()


def _build_keyword_clause(value: str, fields: list[str]) -> str | None:
    words = [_sanitize_term(word) for word in value.split() if _sanitize_term(word)]
    if not words:
        return None
    word_clauses: list[str] = []
    for word in words:
        per_field = [f'{field}="*{word}*"' for field in fields]
        if per_field:
            word_clauses.append("(" + " OR ".join(per_field) + ")")
    if not word_clauses:
        return None
    return "(" + " AND ".join(word_clauses) + ")"


async def _fetch_study_summaries(accessions: list[str]) -> dict[str, dict]:
    if not accessions:
        return {}
    batch = ",".join(accessions)
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.get(f"{ENA_BROWSER_API_BASE.rstrip('/')}/summary/{batch}")
        response.raise_for_status()
        payload = response.json()
    summaries = {}
    for item in payload.get("summaries", []):
        accession = item.get("accession")
        if accession:
            summaries[accession] = item
    return summaries


@mcp.tool
async def search_rna_studies(
    disease: Annotated[
        str | None,
        Field(
            description=(
                "Disease/condition keywords matched against ENA disease and study_title fields (e.g., 'cancer', 'ALS')."
            ),
            examples=["cancer", "ALS"],
            max_length=200,
        ),
    ] = None,
    organism: Annotated[
        str,
        Field(
            description=(
                "Scientific or common organism name; normalized to scientific (e.g., 'human' -> 'Homo sapiens')."
            ),
            examples=["Homo sapiens", "human"],
            max_length=200,
        ),
    ] = DEFAULT_ORGANISM,
    technology: Annotated[
        TechnologyPreset | None,
        Field(
            description=(
                "Technology preset shortcut. Set to None when specifying library_strategies/library_sources directly."
            ),
            examples=["bulk"],
        ),
    ] = "bulk",
    tissue: Annotated[
        str | None,
        Field(
            description=(
                "Tissue or cell-type keywords matched against ENA tissue_type and study_title fields (e.g., 'brain')."
            ),
            examples=["brain", "liver"],
            max_length=200,
        ),
    ] = None,
    library_strategies: Annotated[
        list[LibraryStrategy] | None,
        Field(
            description=("Specific ENA library strategies (e.g., ['RNA-Seq']). Overrides technology preset."),
            examples=[["RNA-Seq"], ["miRNA-Seq", "ncRNA-Seq"]],
        ),
    ] = None,
    library_sources: Annotated[
        list[LibrarySource] | None,
        Field(
            description=("Specific ENA library sources (e.g., ['TRANSCRIPTOMIC']). Overrides technology preset."),
            examples=[["TRANSCRIPTOMIC"], ["TRANSCRIPTOMIC SINGLE CELL"]],
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Max studies to return (default 20, 0 = entire result set up to service caps).",
            ge=0,
        ),
    ] = 20,
) -> dict:
    """Search ENA for RNA sequencing studies with exact run/sample counts."""
    client = ENAClient()

    organism = normalize_organism(organism)
    strategy_enums = list(library_strategies) if library_strategies else None
    source_enums = list(library_sources) if library_sources else None
    library_strategy_values = [s.value for s in strategy_enums] if strategy_enums else None
    library_source_values = [s.value for s in source_enums] if source_enums else None

    rna_filter = build_technology_filter(
        technology=technology,
        library_strategies=strategy_enums,
        library_sources=source_enums,
    )

    query_parts = [f'tax_name("{organism}")', rna_filter]

    if disease:
        disease_clause = _build_keyword_clause(disease, ["disease", "study_title"])
        if disease_clause:
            query_parts.append(disease_clause)

    if tissue:
        tissue_clause = _build_keyword_clause(tissue, ["tissue_type", "study_title"])
        if tissue_clause:
            query_parts.append(tissue_clause)

    study_query = " AND ".join(query_parts)

    filters = {
        "organism": organism,
        "technology": technology,
        "library_strategies": library_strategy_values,
        "library_sources": library_source_values,
        "disease": disease,
        "tissue": tissue,
    }

    if limit < 0:
        return {
            "error": "limit must be >= 0",
            "count": 0,
            "returned": 0,
            "studies": [],
            "filters": filters,
        }

    grouped = await client.aggregate_count(
        result="read_run",
        query=study_query,
        field="study_accession",
        limit=0,
    )

    normalized_grouped: list[tuple[str, int]] = []
    for accession, count in grouped:
        if not accession:
            continue
        normalized_grouped.append((accession.upper(), count))
    grouped = normalized_grouped

    total_studies = len(grouped)
    if total_studies == 0:
        return {
            "count": 0,
            "returned": 0,
            "limit": limit,
            "query_used": study_query,
            "filters": filters,
            "studies": [],
        }

    grouped.sort(key=lambda item: item[1], reverse=True)

    desired = total_studies if limit == 0 else min(limit, total_studies)
    if desired > MAX_STUDY_RESULTS:
        return {
            "error": f"limit too high for a single response (max {MAX_STUDY_RESULTS})",
            "count": total_studies,
            "returned": 0,
            "limit": limit,
            "studies": [],
            "filters": filters,
            "query_used": study_query,
        }

    selected = grouped[:desired]
    if not selected:
        return {
            "error": "limit resulted in zero studies; increase limit to retrieve results.",
            "count": total_studies,
            "returned": 0,
            "limit": limit,
            "query_used": study_query,
            "filters": filters,
            "studies": [],
        }

    selected_accessions = {acc for acc, _ in selected}
    total_runs = sum(count for _, count in selected)
    if total_runs > MAX_RUN_ROWS:
        return {
            "error": "Result exceeds run retrieval cap. Refine filters or lower limit.",
            "count": total_studies,
            "returned": 0,
            "limit": limit,
            "studies": [],
            "cap_runs": MAX_RUN_ROWS,
            "requested_runs": total_runs,
            "filters": filters,
            "query_used": study_query,
        }

    study_clause = "(" + " OR ".join(f'study_accession="{acc}"' for acc in selected_accessions) + ")"
    run_query = f"({study_query}) AND {study_clause}" if study_clause else study_query

    run_fields = ",".join(
        [
            "run_accession",
            "study_accession",
            "secondary_study_accession",
            "study_title",
            "center_name",
            "scientific_name",
            "tax_id",
            "first_public",
            "sample_accession",
            "library_strategy",
            "library_source",
        ]
    )

    run_rows = await client.search(
        result="read_run",
        query=run_query,
        fields=run_fields,
        limit=0,
        format="json",
    )

    run_entries = run_rows if isinstance(run_rows, list) else [run_rows]

    study_meta: dict[str, dict] = {}
    samples_by_study: dict[str, set[str]] = defaultdict(set)
    runs_by_study: dict[str, set[str]] = defaultdict(set)
    strategies_by_study: dict[str, set[str]] = defaultdict(set)
    sources_by_study: dict[str, set[str]] = defaultdict(set)

    for row in run_entries:
        study_acc_raw = row.get("study_accession")
        accession = study_acc_raw.upper() if isinstance(study_acc_raw, str) else study_acc_raw
        if not accession or accession not in selected_accessions:
            continue
        study_meta.setdefault(
            accession,
            {
                "study_accession": accession,
                "secondary_study_accession": row.get("secondary_study_accession"),
                "study_title": row.get("study_title"),
                "center_name": row.get("center_name"),
                "scientific_name": row.get("scientific_name"),
                "tax_id": row.get("tax_id"),
                "first_public": row.get("first_public"),
            },
        )
        if row.get("sample_accession"):
            samples_by_study[accession].add(row["sample_accession"])
        if row.get("run_accession"):
            runs_by_study[accession].add(row["run_accession"])
        if row.get("library_strategy"):
            strategies_by_study[accession].add(row["library_strategy"])
        if row.get("library_source"):
            sources_by_study[accession].add(row["library_source"])

    summary_map = await _fetch_study_summaries(list(selected_accessions))

    ordered = []
    for acc, count in selected:
        meta = study_meta.get(acc)
        if not meta:
            continue
        strategies = sorted(strategies_by_study.get(acc, set()))
        sources = sorted(sources_by_study.get(acc, set()))
        summary = summary_map.get(acc, {})
        ordered.append(
            {
                **meta,
                "run_count": count,
                "run_count_verified": len(runs_by_study.get(acc, set())),
                "sample_count": len(samples_by_study.get(acc, set())),
                "library_strategies": strategies,
                "library_sources": sources,
                "library_strategy": ", ".join(strategies),
                "library_source": ", ".join(sources),
                "description": summary.get("description"),
                "publications": summary.get("publications", []),
                "summary_attributes": summary.get("attributes", []),
            }
        )

    return {
        "count": total_studies,
        "returned": len(ordered),
        "limit": limit,
        "query_used": study_query,
        "filters": filters,
        "studies": ordered,
        "run_cap": MAX_RUN_ROWS,
    }


@mcp.tool
async def list_library_types() -> dict:
    """List all available library strategies and sources for ENA searches.

    **Use this tool to discover what library types are available for filtering.**

    Returns all controlled vocabulary values for library_strategy and library_source
    that can be used with search_rna_studies().

    Returns
    -------
    dict
        Dictionary with keys:
        - library_strategies: List of dicts with "value" and "name"
        - library_sources: List of dicts with "value" and "name"
        - rna_strategies: Filtered list of RNA-related strategies only
        - summary: Counts of available options

    Examples
    --------
    Get all available options:
        list_library_types()
        # Returns full list of ~50 strategies and 9 sources

    Use returned values in search:
        # 1. Call list_library_types() to see options
        # 2. Pick strategies from the returned list
        # 3. Use in search_rna_studies(library_strategies=["Ribo-Seq"], technology=None)
    """
    # Get all strategies from enum
    strategies = [
        {
            "value": strategy.value,
            "name": strategy.name,
        }
        for strategy in LibraryStrategy
    ]

    # Get all sources from enum
    sources = [
        {
            "value": source.value,
            "name": source.name,
        }
        for source in LibrarySource
    ]

    # Filter RNA-related strategies
    rna_related = [
        "RNA-Seq",
        "snRNA-seq",
        "ssRNA-seq",
        "miRNA-Seq",
        "ncRNA-Seq",
        "FL-cDNA",
        "EST",
        "Ribo-Seq",
        "RIP-Seq",
    ]
    rna_strategies = [s for s in strategies if s["value"] in rna_related]

    return {
        "library_strategies": strategies,
        "library_sources": sources,
        "rna_strategies": rna_strategies,
        "summary": {
            "total_strategies": len(strategies),
            "total_sources": len(sources),
            "rna_strategies_count": len(rna_strategies),
        },
        "usage_hint": (
            "Use the 'value' field in search_rna_studies(library_strategies=[...], "
            "library_sources=[...], technology=None)"
        ),
    }
