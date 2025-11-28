"""Tool for finding studies related to publications."""

from typing import Annotated

from pydantic import Field

from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp


@mcp.tool
async def find_studies_by_publication(
    pubmed_id: Annotated[
        str,
        Field(
            description="PubMed ID to search for. Note: This tool has known API limitations and will return an error with alternative instructions",
            examples=["36913357", "33247152"],
        ),
    ],
) -> dict:
    """Find ENA studies by PubMed ID (API limitation - returns error with workaround).

    Usage Tips
    ----------
    ENA Portal API doesn't expose pubmed_id as a searchable field. This tool documents the
    limitation for LLM awareness. Instead: use search_studies_by_keywords() with publication
    terms, then call get_study_details() to check the publications array for matching PubMed IDs.

    Returns
    -------
    dict
        Dictionary containing:
        - error: API limitation message with recommended workflow
        - pubmed_id: Provided PubMed ID
        - count: Always 0
        - studies: Always empty list
    """
    # Note: pubmed_id field is not available in ENA Portal API
    return {
        "error": (
            "PubMed ID search is not supported by the ENA Portal API. "
            "The pubmed_id field is not available for searching. "
            "Alternative: Use search_studies_by_keywords() with publication keywords, "
            "or search directly on the ENA Browser (https://www.ebi.ac.uk/ena/browser/)."
        ),
        "pubmed_id": pubmed_id,
        "count": 0,
        "studies": [],
    }


@mcp.tool
async def search_studies_by_keywords(
    keywords: Annotated[
        str,
        Field(
            description="Keywords to search for in study titles and descriptions (e.g., 'immune response', 'transcription factor'). Multi-word phrases are automatically split into individual words that must all match",
            examples=["immune response", "breast cancer", "RNA binding protein", "transcriptome", "cell cycle"],
        ),
    ],
    include_title: Annotated[
        bool,
        Field(
            description="Whether to search in study titles (recommended: keep True)",
        ),
    ] = True,
    include_description: Annotated[
        bool,
        Field(
            description="Whether to search in study descriptions. This searches sample-level descriptions and may broaden results",
        ),
    ] = True,
    organism: Annotated[
        str | None,
        Field(
            description="Optionally filter by organism. Use common name like 'human' or scientific name like 'Homo sapiens'. Leave as None to search across all organisms",
            examples=["Homo sapiens", "Mus musculus", "human", "mouse", None],
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="How many studies to return. Start with 20, increase if needed",
            ge=1,
            examples=[20, 50, 100],
        ),
    ] = 20,
) -> dict:
    """Search for studies using flexible keyword matching across titles and descriptions.

    **When to use this tool**: Use this for broad exploratory searches when search_rna_studies()
    is too restrictive. Good for:
    - Searching by biological processes, pathways, or molecular mechanisms
    - Finding studies about specific genes, proteins, or complexes
    - Searching by methodology when you don't know the specific disease
    - General exploratory searches across many study types

    **Important notes**:
    - Searches both study-level titles AND sample-level descriptions
    - Multi-word keywords are split: "breast cancer" searches for "breast" AND "cancer"
    - May return studies where only one sample mentions your keywords
    - Results can be broader than search_rna_studies() disease/tissue filters

    **Search tips**:
    - Try keyword variations and abbreviations if no results (e.g., "immune response" vs "immunity")
    - Try broader or narrower terms (e.g., "transcription" vs "transcription factor binding")
    - Consider searching multiple organisms if limited results in one species
    - Use organism filter to narrow down results to specific species

    Returns
    -------
    dict
        Search results containing:
        - count: How many total studies match
        - returned: How many studies in this response
        - keywords_used: What keywords were searched
        - organism_filter: What organism filter was applied (if any)
        - studies: List of matching studies with accession, title, organism, and other metadata
    """
    client = ENAClient()

    # Build search query for text fields
    # Note: ENA Portal API doesn't support wildcards in multi-word phrases
    # Split keywords into words and search for each
    keyword_words = keywords.split()

    text_parts = []
    if include_title:
        if len(keyword_words) == 1:
            text_parts.append(f'study_title="*{keywords}*"')
        else:
            # Multiple words - search for each word
            word_queries = [f'study_title="*{word}*"' for word in keyword_words]
            text_parts.append(f"({' AND '.join(word_queries)})")

    if include_description:
        # Use generic description field (applies to samples) as fallback
        if len(keyword_words) == 1:
            text_parts.append(f'description="*{keywords}*"')
        else:
            word_queries = [f'description="*{word}*"' for word in keyword_words]
            text_parts.append(f"({' AND '.join(word_queries)})")

    if not text_parts:
        return {
            "error": "Must search in at least title or description",
            "count": 0,
            "studies": [],
        }

    # Combine text searches with OR
    text_query = " OR ".join(text_parts)

    # Add organism filter if provided
    if organism:
        query = f'({text_query}) AND tax_name("{organism}")'
    else:
        query = f"({text_query})"

    # Get count
    count = await client.count(result="read_study", query=query)

    # Get results
    # Note: read_study doesn't have study_description field
    fields = (
        "study_accession,secondary_study_accession,study_title,"
        "tax_id,scientific_name,center_name,first_public,"
        "library_strategy"
    )

    results = await client.search(
        result="read_study",
        query=query,
        fields=fields,
        limit=limit,
        format="json",
    )

    return {
        "count": count,
        "returned": len(results) if isinstance(results, list) else 1 if results else 0,
        "keywords_used": keywords,
        "organism_filter": organism,
        "studies": results if isinstance(results, list) else [results] if results else [],
    }
