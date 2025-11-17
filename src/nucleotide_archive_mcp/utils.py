"""Utility functions for RNA dataset search."""

from nucleotide_archive_mcp.config import (
    COMMON_ORGANISMS,
    TECHNOLOGY_PRESETS,
    LibrarySource,
    LibraryStrategy,
)


def normalize_organism(organism: str) -> str:
    """Normalize organism name to scientific name.

    Parameters
    ----------
    organism : str
        Organism name (common or scientific)

    Returns
    -------
    str
        Scientific name
    """
    # Check if it's already a scientific name (contains space)
    if " " in organism:
        return organism

    # Try to map from common names (case-insensitive)
    return COMMON_ORGANISMS.get(organism.lower(), organism)


def build_technology_filter(
    technology: str | None = None,
    library_strategies: list[LibraryStrategy] | None = None,
    library_sources: list[LibrarySource] | None = None,
) -> str:
    """Build library strategy and source filter from technology preset or specific values.

    Parameters
    ----------
    technology : str, optional
        Technology preset: "bulk", "single-cell", "small-rna", "ribo-seq", or "rna-all"
    library_strategies : list[LibraryStrategy], optional
        Specific library strategies to filter by (overrides technology)
    library_sources : list[LibrarySource], optional
        Specific library sources to filter by (overrides technology)

    Returns
    -------
    str
        ENA query filter string
    """
    # If specific strategies/sources provided, use those
    if library_strategies or library_sources:
        strategies = [s.value for s in (library_strategies or [])]
        sources = [s.value for s in (library_sources or [])]
    # Otherwise use technology preset
    elif technology:
        preset = TECHNOLOGY_PRESETS.get(technology.lower())
        if not preset:
            # Default to bulk
            preset = TECHNOLOGY_PRESETS["bulk"]
        strategies = preset["strategies"]  # type: ignore[assignment]
        sources = preset["sources"]  # type: ignore[assignment]
    else:
        # Default to bulk
        preset = TECHNOLOGY_PRESETS["bulk"]
        strategies = preset["strategies"]  # type: ignore[assignment]
        sources = preset["sources"]  # type: ignore[assignment]

    # Build conditions
    strategy_parts = [f'library_strategy="{s}"' for s in strategies]
    source_parts = [f'library_source="{s}"' for s in sources]

    # If no strategies specified, use sources only
    if not strategies and sources:
        return f"({' OR '.join(source_parts)})"

    # If no sources specified, use strategies only
    if strategies and not sources:
        return f"({' OR '.join(strategy_parts)})"

    # Single-cell special case: just use source (more specific)
    if technology and technology.lower() == "single-cell":
        return f"({' OR '.join(source_parts)})"

    # Simple case: single strategy + single source
    if len(strategies) == 1 and len(sources) == 1:
        return f"({strategy_parts[0]} AND {source_parts[0]})"

    # Complex case: cross-product of strategies × sources
    conditions = []
    for strat_part in strategy_parts:
        for source_part in source_parts:
            conditions.append(f"({strat_part} AND {source_part})")

    return f"({' OR '.join(conditions)})"
