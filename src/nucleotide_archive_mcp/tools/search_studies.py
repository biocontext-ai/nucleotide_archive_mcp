"""Tool for searching RNA-seq studies in ENA."""

from typing import Annotated

from nucleotide_archive_mcp.config import DEFAULT_ORGANISM, LibrarySource, LibraryStrategy
from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp
from nucleotide_archive_mcp.utils import build_technology_filter, normalize_organism


@mcp.tool
async def search_rna_studies(
    disease: Annotated[
        str | None, "Disease or condition (e.g., 'cancer', 'diabetes'). Leave empty for all studies."
    ] = None,
    organism: Annotated[str, "Scientific or common organism name"] = DEFAULT_ORGANISM,
    technology: Annotated[
        str | None,
        "Technology preset: 'bulk', 'single-cell', 'small-rna', 'ribo-seq', 'rna-all'. Leave None to specify library_strategies/library_sources directly.",
    ] = "bulk",
    tissue: Annotated[str | None, "Tissue or cell type (e.g., 'brain', 'liver', 'blood')"] = None,
    library_strategies: Annotated[
        list[str] | None,
        "Specific library strategies (e.g., ['RNA-Seq', 'miRNA-Seq']). Overrides technology preset.",
    ] = None,
    library_sources: Annotated[
        list[str] | None,
        "Specific library sources (e.g., ['TRANSCRIPTOMIC']). Overrides technology preset.",
    ] = None,
    limit: Annotated[int, "Max results (20 default, 0=all). No pagination support."] = 20,
) -> dict:
    """Search for RNA sequencing studies in the European Nucleotide Archive.

    **Primary use case**: Finding disease-related RNA-seq datasets in human/mouse for
    hypothesis validation. Returns study accessions that can be passed to get_study_details()
    for full metadata including publications.

    **Two Search Modes**:

    1. **Preset Mode (Simple)**: Use `technology` parameter with preset filters:
       - "bulk": Standard bulk RNA-seq
       - "single-cell": Single-cell/nucleus RNA-seq
       - "small-rna": microRNA and ncRNA sequencing
       - "ribo-seq": Ribosome profiling
       - "rna-all": All RNA sequencing types

    2. **Advanced Mode**: Use `library_strategies` and/or `library_sources` for precise control:
       - library_strategies: ["RNA-Seq", "miRNA-Seq", "Ribo-Seq", ...]
       - library_sources: ["TRANSCRIPTOMIC", "TRANSCRIPTOMIC SINGLE CELL", ...]
       - Call list_library_types() to see all available values

    **LLM Usage Pattern**:
    1. Call this tool to find studies matching research criteria
    2. Extract study_accession from results
    3. Call get_study_details(study_accession) for full metadata & publications
    4. Optionally call get_download_urls() or generate_download_script() for data files

    **API Limitations**:
    - No offset-based pagination. Use limit=0 for all results (slow).
    - Multi-word disease searches: Automatically splits into individual words
      (e.g., "Fabry nephropathy" → searches for "Fabry" AND "nephropathy")
      because the API doesn't support wildcards in multi-word phrases.

    Parameters
    ----------
    disease : str, optional
        Disease/condition keyword searched in study titles. Examples: "cancer", "diabetes",
        "Alzheimer", "cardiovascular", "infection". Leave None for all studies.
    organism : str, optional
        Scientific or common organism name. Default: "Homo sapiens" (human).
        Scientific names: "Mus musculus" (mouse), "Rattus norvegicus" (rat).
        Common names: "human", "mouse", "rat", "zebrafish", "fly", "worm", "yeast".
    technology : str, optional
        Technology preset filter (default: "bulk"). Set to None to use library_strategies/library_sources.
        Presets: "bulk", "single-cell", "small-rna", "ribo-seq", "rna-all"
    tissue : str, optional
        Tissue/cell type filter. Searches study_title, cell_type, tissue_type fields.
        Examples: "brain", "liver", "blood", "heart", "kidney"
    library_strategies : list[str], optional
        Specific library strategies to filter by (overrides technology preset).
        Examples: ["RNA-Seq"], ["miRNA-Seq", "ncRNA-Seq"], ["ChIP-Seq"]
        Use list_library_types() to see all ~50 available values.
    library_sources : list[str], optional
        Specific library sources to filter by (overrides technology preset).
        Examples: ["TRANSCRIPTOMIC"], ["TRANSCRIPTOMIC SINGLE CELL"], ["GENOMIC"]
    limit : int, optional
        Maximum results (default: 20). Set to 0 for all (may be slow). No pagination.

    Returns
    -------
    dict
        Dictionary with keys:
        - count (int): Total matching studies
        - returned (int): Number of studies in this response
        - limit (int): Applied limit
        - query_used (str): Actual ENA API query executed
        - filters (dict): Applied filters summary
        - studies (list[dict]): Study records, each containing:
            - study_accession: Primary accession (use with get_study_details)
            - secondary_study_accession: Alternative accession
            - study_title: Brief description
            - tax_id: NCBI taxonomy ID
            - scientific_name: Organism name
            - center_name: Submitting institution
            - first_public: Publication date
            - library_strategy: Sequencing strategy
            - library_source: Source material type
        - error (str, optional): Error message if validation failed

    Examples
    --------
    **Simple searches with presets:**

    Find human cancer bulk RNA-seq:
        disease="cancer"  # Uses all defaults

    Find mouse diabetes single-cell studies:
        disease="diabetes", organism="mouse", technology="single-cell"

    Find human brain tissue studies:
        tissue="brain", limit=50

    **Advanced searches with specific library types:**

    Find ribosome profiling studies:
        library_strategies=["Ribo-Seq"], technology=None

    Find small RNA studies (miRNA + ncRNA):
        library_strategies=["miRNA-Seq", "ncRNA-Seq"], technology=None

    Find ChIP-Seq studies in cancer:
        library_strategies=["ChIP-Seq"], disease="cancer", technology=None

    Find only single-cell data (any strategy):
        library_sources=["TRANSCRIPTOMIC SINGLE CELL"], technology=None
    """
    client = ENAClient()

    # Normalize organism name (e.g., "human" -> "Homo sapiens")
    organism = normalize_organism(organism)

    # Validate library strategies if provided
    if library_strategies:
        valid_strategies = {s.value for s in LibraryStrategy}
        invalid = [s for s in library_strategies if s not in valid_strategies]
        if invalid:
            return {
                "error": f"Invalid library strategies: {invalid}. Use list_library_types() to see valid values.",
                "valid_strategies": sorted(valid_strategies),
                "count": 0,
                "returned": 0,
                "studies": [],
            }
        # Convert strings to enum for type safety
        strategy_enums = [LibraryStrategy(s) for s in library_strategies]
    else:
        strategy_enums = None

    # Validate library sources if provided
    if library_sources:
        valid_sources = {s.value for s in LibrarySource}
        invalid = [s for s in library_sources if s not in valid_sources]
        if invalid:
            return {
                "error": f"Invalid library sources: {invalid}. Use list_library_types() to see valid values.",
                "valid_sources": sorted(valid_sources),
                "count": 0,
                "returned": 0,
                "studies": [],
            }
        # Convert strings to enum for type safety
        source_enums = [LibrarySource(s) for s in library_sources]
    else:
        source_enums = None

    # Build the query
    query_parts = []

    # Always filter by organism
    query_parts.append(f'tax_name("{organism}")')

    # Add library strategy/source filter
    library_filter = build_technology_filter(
        technology=technology,
        library_strategies=strategy_enums,
        library_sources=source_enums,
    )
    query_parts.append(library_filter)

    # Add disease filter if provided
    if disease:
        # Search for disease in study title
        # Note: ENA Portal API doesn't support wildcards in multi-word phrases
        # e.g., study_title="*Fabry nephropathy*" returns 0 results
        # but study_title="*Fabry*" AND study_title="*nephropathy*" works
        # Split disease into words and search for each
        disease_words = disease.split()
        if len(disease_words) == 1:
            # Single word - simple wildcard search
            disease_query = f'study_title="*{disease}*"'
        else:
            # Multiple words - search for each word separately with AND
            word_queries = [f'study_title="*{word}*"' for word in disease_words]
            disease_query = f"({' AND '.join(word_queries)})"
        query_parts.append(disease_query)

    # Add tissue filter if provided
    if tissue:
        # Search in study title, cell_type, and tissue_type fields
        tissue_query = f'(study_title="*{tissue}*" OR cell_type="*{tissue}*" OR tissue_type="*{tissue}*")'
        query_parts.append(tissue_query)

    # Combine all query parts
    query = " AND ".join(query_parts)

    # Get total count
    count = await client.count(result="read_study", query=query)

    # Get actual results
    # Note: read_study doesn't have study_description field, only study_title
    # Include library_source and library_strategy to show technology type
    fields = (
        "study_accession,secondary_study_accession,study_title,"
        "tax_id,scientific_name,center_name,first_public,last_updated,"
        "library_strategy,library_source"
    )

    results = await client.search(
        result="read_study",
        query=query,
        fields=fields,
        limit=limit,
        format="json",
    )

    # Format the response with applied filters
    return {
        "count": count,
        "returned": len(results) if isinstance(results, list) else 1,
        "limit": limit,
        "query_used": query,
        "filters": {
            "organism": organism,
            "technology": technology,
            "library_strategies": library_strategies,
            "library_sources": library_sources,
            "disease": disease,
            "tissue": tissue,
        },
        "studies": results if isinstance(results, list) else [results],
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
