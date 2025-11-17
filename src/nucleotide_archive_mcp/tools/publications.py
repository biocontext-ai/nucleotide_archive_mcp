"""Tool for finding studies related to publications."""

from typing import Annotated

from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp


@mcp.tool
async def find_studies_by_publication(
    pubmed_id: Annotated[str, "PubMed ID (e.g., '36913357'). API limitation: returns error."],
) -> dict:
    """Find ENA studies by PubMed ID (CURRENTLY LIMITED - see alternative below).

    **API LIMITATION**: ENA Portal API doesn't expose pubmed_id as searchable field.
    This tool returns an error. Instead:

    **Recommended Alternative Workflow**:
    1. Use search_studies_by_keywords() with terms from the publication
    2. Call get_study_details() on results to check publications[] array
    3. Match publications[].pubmed_id to find the right study

    **Why this exists**: Documented limitation for LLM awareness. Use get_study_details()
    to retrieve PubMed IDs from studies, not to search by them.

    Parameters
    ----------
    pubmed_id : str
        PubMed ID (e.g., "36913357"). Tool will return error about limitation.

    Returns
    -------
    dict
        Error dict with alternative instructions

    Examples
    --------
    Will return API limitation error:
        pubmed_id="33247152"
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
    keywords: Annotated[str, "Keywords to search (e.g., 'immune response', 'breast cancer')"],
    include_title: Annotated[bool, "Search in study titles"] = True,
    include_description: Annotated[bool, "Search in descriptions (may match samples too)"] = True,
    organism: Annotated[str | None, "Filter by organism (e.g., 'Homo sapiens')"] = None,
    limit: Annotated[int, "Max results (default: 20)"] = 20,
) -> dict:
    """Flexible keyword search across study titles and descriptions.

    **LLM Usage**: Use when search_rna_studies() is too specific (disease-only). Good for:
    - Broad exploratory searches
    - Finding studies by biological process/pathway terms
    - Searching when you know methodology but not disease

    **Note**:
    - Searches title (study-level) and description (sample-level) fields, so may
      return studies where only one sample matches keywords.
    - Multi-word keywords are automatically split and searched individually
      (e.g., "breast cancer" → searches for "breast" AND "cancer").

    Parameters
    ----------
    keywords : str
        Keywords to find (e.g., "immune response", "breast cancer", "RNA binding protein").
        Wildcards (*) automatically added.
    include_title : bool, optional
        Search study_title field (study-level). Default: True.
    include_description : bool, optional
        Search description field (sample-level). May broaden results. Default: True.
    organism : str, optional
        Filter by NCBI scientific name (e.g., "Homo sapiens"). None=all organisms.
    limit : int, optional
        Max results (default: 20).

    Returns
    -------
    dict
        - count (int): Total matching studies
        - returned (int): Studies in this response
        - keywords_used (str): Keywords searched
        - organism_filter (str|None): Organism filter applied
        - studies (list[dict]): Matching studies

    Examples
    --------
    Find human immune response studies:
        keywords="immune response", organism="Homo sapiens"

    Broad search across all organisms:
        keywords="transcriptome", limit=50
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
