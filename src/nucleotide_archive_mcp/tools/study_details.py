"""Tool for getting detailed study information."""

from typing import Annotated, Any

import httpx

from nucleotide_archive_mcp.config import DEFAULT_TIMEOUT, ENA_BROWSER_API_BASE
from nucleotide_archive_mcp.mcp import mcp


@mcp.tool
async def get_study_details(
    study_accession: Annotated[str, "Study accession from search results (e.g., 'SRP417965', 'PRJNA123456')"],
) -> dict:
    """Get comprehensive metadata for a specific ENA study including publications.

    **LLM Usage**: Call this AFTER search_rna_studies() to get full study metadata including
    descriptions and PubMed IDs. This uses the ENA Browser API which provides richer metadata
    than search results.

    **Typical workflow**:
    1. search_rna_studies() → get list of studies
    2. get_study_details() → get full metadata for interesting studies (THIS TOOL)
    3. Extract publications[].pubmed_id if you need to reference papers
    4. get_download_urls() or generate_download_script() → get data files

    **Key feature**: Returns `publications` array with PubMed IDs, unlike search results.

    Parameters
    ----------
    study_accession : str
        Study accession from search_rna_studies results. Accepts multiple formats:
        - SRP/ERP/DRP: Sequence Read Archive format (e.g., "SRP417965")
        - PRJNA/PRJEB/PRJDB: BioProject format (e.g., "PRJNA123456")

    Returns
    -------
    dict
        - accession (str): Study accession
        - title (str): Brief study title
        - description (str): Detailed study description (full abstract/methods)
        - publications (list[dict]): Associated publications, each with:
            - pubmed_id (str): PubMed ID for the paper
            - source (str): "PubMed"
        - center_name (str): Submitting institution
        - alias (str): Submitter's study name (often GSE accession for GEO)
        - data_type (str): Usually "STUDY"
        - status (str): "public" or "private"
        - first_public (str): Date made public (YYYY-MM-DD)
        - last_updated (str): Last modification date (YYYY-MM-DD)
        - file_report_links (list[dict]): Direct API links for file reports
        - error (str|None): Error message if study not found

    Examples
    --------
    Get full metadata after search:
        study_accession="SRP417965"

    Check if study has publications:
        study_accession="PRJDB2345"
    """
    try:
        # Use ENA Browser API for rich metadata including publications
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http_client:
            response = await http_client.get(
                f"{ENA_BROWSER_API_BASE}/summary/{study_accession}",
                params={"offset": 0, "limit": 100},
            )
            response.raise_for_status()
            browser_data = response.json()

        if not browser_data.get("summaries"):
            return {
                "error": f"Study {study_accession} not found",
                "accession": study_accession,
            }

        summary = browser_data["summaries"][0]

        # Extract publications with PubMed IDs
        publications: list[dict[str, Any]] = []
        for pub in summary.get("publications", []):
            if pub.get("source") == "pubmed":
                publications.append({"pubmed_id": pub.get("pId"), "source": "PubMed"})

        # Extract attributes
        attributes = {attr["tag"]: attr["value"] for attr in summary.get("attributes", [])}

        # Get file report links
        file_links = []
        for pub in summary.get("publications", []):
            if pub.get("source") in ("ENA-FASTQ-FILES", "ENA-SUBMITTED-FILES"):
                file_links.append({"type": pub["source"], "url": pub["pId"]})

        return {
            "accession": summary.get("accession"),
            "title": summary.get("title"),
            "description": summary.get("description"),
            "center_name": summary.get("centerName"),
            "alias": summary.get("alias"),
            "data_type": summary.get("dataType"),
            "status": summary.get("statusDescription"),
            "first_public": attributes.get("ENA-FIRST-PUBLIC"),
            "last_updated": attributes.get("ENA-LAST-UPDATE"),
            "publications": publications,
            "file_report_links": file_links,
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "error": f"Study {study_accession} not found in ENA",
                "accession": study_accession,
            }
        return {
            "error": f"HTTP error retrieving study: {e!s}",
            "accession": study_accession,
        }
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to retrieve study details: {e!s}",
            "accession": study_accession,
        }
