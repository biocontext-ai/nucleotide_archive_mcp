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
    try:
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
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 301:
            return {}
        raise
    except httpx.HTTPError:
        return {}


@mcp.tool
async def search_rna_studies(
    disease: Annotated[
        str | None,
        Field(
            description="Disease/condition keywords to search for (e.g., 'cancer', 'ALS'). Matched against disease and study_title fields",
            examples=["cancer", "ALS", "diabetes", "Alzheimer"],
            max_length=200,
        ),
    ] = None,
    organism: Annotated[
        str | None,
        Field(
            description="Organism to search for. Use common names like 'human' or 'mouse', or scientific names like 'Homo sapiens'. Leave as None to search across all species",
            examples=["Homo sapiens", "human", "Mus musculus", "mouse", "zebrafish", "rat", None],
            max_length=200,
        ),
    ] = None,
    technology: Annotated[
        TechnologyPreset | None,
        Field(
            description="RNA sequencing technology type: 'bulk' for standard RNA-Seq, 'single-cell' for scRNA-seq, 'small-rna' for miRNA/small RNA, 'ribo-seq' for ribosome profiling, 'rna-all' for any RNA technology. Set to None when using library_strategies/library_sources directly",
            examples=["bulk", "single-cell", "small-rna"],
        ),
    ] = "bulk",
    tissue: Annotated[
        str | None,
        Field(
            description="Tissue or cell type keywords to search for (e.g., 'brain', 'liver'). Matched against tissue_type and study_title fields",
            examples=["brain", "liver", "heart", "kidney"],
            max_length=200,
        ),
    ] = None,
    library_strategies: Annotated[
        list[LibraryStrategy] | None,
        Field(
            description="Advanced: Specific sequencing strategies to filter by (e.g., ['RNA-Seq']). Overrides the technology preset. Call list_library_types() first to see all available options",
            examples=[["RNA-Seq"], ["miRNA-Seq", "ncRNA-Seq"]],
        ),
    ] = None,
    library_sources: Annotated[
        list[LibrarySource] | None,
        Field(
            description="Advanced: Specific library source materials to filter by (e.g., ['TRANSCRIPTOMIC']). Overrides the technology preset. Call list_library_types() first to see all available options",
            examples=[["TRANSCRIPTOMIC"], ["TRANSCRIPTOMIC SINGLE CELL"]],
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="How many studies to return. Use 20 for initial searches, increase if needed. Set to 0 to get all results (up to system limits)",
            ge=0,
            examples=[20, 50, 0],
        ),
    ] = 20,
) -> dict:
    """Search for RNA sequencing studies by disease, tissue, and organism.

    **When to use this tool**: Primary search tool for finding RNA-seq datasets when you know
    the disease/condition OR tissue/cell-type you're interested in. Use search_studies_by_keywords()
    for broader searches by biological processes or methodology.

    **Default behavior**: Searches across ALL organisms unless you specify one. This helps find
    relevant datasets across multiple species (human, mouse, rat, etc.).

    **Search tips**:
    - Try different keyword variations if no results (e.g., "ALS" vs "amyotrophic lateral sclerosis")
    - Try broader terms (e.g., "neurodegeneration" instead of specific disease)
    - Search all organisms first (organism=None), then filter to specific species if needed
    - Use tissue parameter to narrow results to specific anatomical sites

    Returns
    -------
    dict
        Search results containing:
        - count: How many total studies match your search
        - returned: How many studies are in this response
        - studies: List of matching studies with titles, sample counts, and publication info
        - query_used: The exact search query that was executed
        - filters: What filters were applied to your search
    """
    client = ENAClient()

    organism = normalize_organism(organism) if organism else None
    strategy_enums = list(library_strategies) if library_strategies else None
    source_enums = list(library_sources) if library_sources else None
    library_strategy_values = [s.value for s in strategy_enums] if strategy_enums else None
    library_source_values = [s.value for s in source_enums] if source_enums else None

    rna_filter = build_technology_filter(
        technology=technology,
        library_strategies=strategy_enums,
        library_sources=source_enums,
    )

    query_parts = [rna_filter]
    if organism:
        query_parts.insert(0, f'tax_name("{organism}")')

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

    Usage Tips
    ----------
    Use to discover available library types for filtering in search_rna_studies(). Returns all
    controlled vocabulary values for library_strategy and library_source. Call this before using
    the advanced library_strategies or library_sources parameters in search_rna_studies().

    Returns
    -------
    dict
        Dictionary with keys:
        - library_strategies: List of all strategies with "value" and "name"
        - library_sources: List of all sources with "value" and "name"
        - rna_strategies: Filtered list of RNA-related strategies only
        - summary: Counts of available options
        - usage_hint: How to use values in search_rna_studies()
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
