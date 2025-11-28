"""Tool for getting detailed study information."""

from typing import Annotated, Any

import httpx

from nucleotide_archive_mcp.config import DEFAULT_TIMEOUT, ENA_BROWSER_API_BASE
from nucleotide_archive_mcp.mcp import mcp

EUROPEPMC_API_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


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
            if pub.get("source", "").upper() == "PUBMED":
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


@mcp.tool
async def get_study_publications(
    study_accession: Annotated[str, "Study accession (e.g., 'SRP417965', 'PRJNA802133')"],
) -> dict:
    """Get detailed publication information for a study from ENA and Europe PMC.

    **LLM Usage**: Use this to get comprehensive publication details including:
    - Full title, authors, and abstract
    - Journal information and DOI
    - Publication date and citation count
    - Full text links (if available)
    - Author affiliations and ORCID IDs

    **Workflow**:
    1. First calls ENA Browser API to get PubMed IDs for the study
    2. Then queries Europe PMC for detailed publication metadata
    3. Returns enriched publication information

    Parameters
    ----------
    study_accession : str
        Study accession from search_rna_studies results. Accepts:
        - SRP/ERP/DRP format (e.g., "SRP417965")
        - PRJNA/PRJEB/PRJDB format (e.g., "PRJNA802133")

    Returns
    -------
    dict
        - accession (str): Study accession
        - publication_count (int): Number of publications found
        - publications (list[dict]): Detailed publication data, each with:
            - pubmed_id (str): PubMed ID
            - pmcid (str|None): PubMed Central ID
            - doi (str|None): Digital Object Identifier
            - title (str): Publication title
            - authors (list[str]): Author names
            - first_author (str|None): First author name
            - last_author (str|None): Last author name
            - journal (str|None): Journal name
            - publication_year (int|None): Year published
            - publication_date (str|None): Full publication date
            - abstract (str|None): Publication abstract
            - citation_count (int|None): Times cited
            - is_open_access (bool): Whether open access
            - full_text_urls (list[dict]|None): Available full text links
            - author_affiliations (list[dict]|None): Detailed author info with ORCID
        - error (str|None): Error message if any

    Examples
    --------
    Get publication details for a study:
        study_accession="PRJNA802133"

    Find papers associated with dataset:
        study_accession="SRP417965"
    """
    try:
        # Step 1: Get PubMed IDs from ENA Browser API
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http_client:
            ena_response = await http_client.get(
                f"{ENA_BROWSER_API_BASE}/summary/{study_accession}",
                params={"offset": 0, "limit": 100},
            )
            ena_response.raise_for_status()
            ena_data = ena_response.json()

        if not ena_data.get("summaries"):
            return {
                "error": f"Study {study_accession} not found",
                "accession": study_accession,
                "publication_count": 0,
                "publications": [],
            }

        summary = ena_data["summaries"][0]

        # Extract PubMed IDs
        pubmed_ids = []
        for pub in summary.get("publications", []):
            if pub.get("source", "").upper() == "PUBMED":
                pubmed_ids.append(pub.get("pId"))

        if not pubmed_ids:
            return {
                "accession": study_accession,
                "publication_count": 0,
                "publications": [],
                "error": None,
            }

        # Step 2: Fetch detailed publication info from Europe PMC
        publications = []
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http_client:
            for pubmed_id in pubmed_ids:
                try:
                    pmc_response = await http_client.get(
                        f"{EUROPEPMC_API_BASE}/search",
                        params={
                            "query": f"ext_id:{pubmed_id}",
                            "resultType": "core",
                            "format": "json",
                        },
                    )
                    pmc_response.raise_for_status()
                    pmc_data = pmc_response.json()

                    # Extract publication details
                    if pmc_data.get("resultList", {}).get("result"):
                        result = pmc_data["resultList"]["result"][0]

                        # Extract author information with affiliations
                        author_details = []
                        if "authorList" in result and "author" in result["authorList"]:
                            for author in result["authorList"]["author"]:
                                author_info = {
                                    "full_name": author.get("fullName"),
                                    "first_name": author.get("firstName"),
                                    "last_name": author.get("lastName"),
                                    "initials": author.get("initials"),
                                    "orcid": None,
                                    "affiliations": [],
                                }

                                # Extract ORCID if available
                                if "authorId" in author:
                                    author_id = author["authorId"]
                                    if isinstance(author_id, dict):
                                        if author_id.get("type") == "ORCID":
                                            author_info["orcid"] = author_id.get("value")
                                    elif isinstance(author_id, list):
                                        for aid in author_id:
                                            if isinstance(aid, dict) and aid.get("type") == "ORCID":
                                                author_info["orcid"] = aid.get("value")
                                                break

                                # Extract affiliations
                                if "authorAffiliationDetailsList" in author:
                                    aff_list = author["authorAffiliationDetailsList"]
                                    if "authorAffiliation" in aff_list:
                                        for aff in aff_list["authorAffiliation"]:
                                            if isinstance(aff, dict) and "affiliation" in aff:
                                                author_info["affiliations"].append(aff["affiliation"])

                                author_details.append(author_info)

                        # Extract simple author name list
                        author_names = [a["full_name"] for a in author_details if a.get("full_name")]

                        # Extract full text URLs
                        full_text_urls = []
                        if "fullTextUrlList" in result and "fullTextUrl" in result["fullTextUrlList"]:
                            for url_info in result["fullTextUrlList"]["fullTextUrl"]:
                                full_text_urls.append(
                                    {
                                        "url": url_info.get("url"),
                                        "availability": url_info.get("availability"),
                                        "document_style": url_info.get("documentStyle"),
                                        "site": url_info.get("site"),
                                    }
                                )

                        # Extract journal info
                        journal_info = result.get("journalInfo", {})

                        publication = {
                            "pubmed_id": pubmed_id,
                            "pmcid": result.get("pmcid"),
                            "doi": result.get("doi"),
                            "title": result.get("title"),
                            "authors": author_names,
                            "first_author": author_names[0] if author_names else None,
                            "last_author": author_names[-1] if len(author_names) > 1 else None,
                            "author_details": author_details,
                            "journal": journal_info.get("journal", {}).get("title"),
                            "journal_issn": journal_info.get("journal", {}).get("essn")
                            or journal_info.get("journal", {}).get("issn"),
                            "publication_year": journal_info.get("yearOfPublication"),
                            "publication_date": result.get("firstPublicationDate")
                            or result.get("electronicPublicationDate"),
                            "abstract": result.get("abstractText"),
                            "citation_count": result.get("citedByCount"),
                            "is_open_access": result.get("isOpenAccess") == "Y",
                            "in_epmc": result.get("inEPMC") == "Y",
                            "in_pmc": result.get("inPMC") == "Y",
                            "has_pdf": result.get("hasPDF") == "Y",
                            "full_text_urls": full_text_urls if full_text_urls else None,
                        }

                        publications.append(publication)

                except httpx.HTTPError as e:
                    # Continue with other publications if one fails
                    publications.append(
                        {
                            "pubmed_id": pubmed_id,
                            "error": f"Failed to fetch publication details: {e!s}",
                        }
                    )

        return {
            "accession": study_accession,
            "publication_count": len(publications),
            "publications": publications,
            "error": None,
        }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "error": f"Study {study_accession} not found in ENA",
                "accession": study_accession,
                "publication_count": 0,
                "publications": [],
            }
        return {
            "error": f"HTTP error retrieving study: {e!s}",
            "accession": study_accession,
            "publication_count": 0,
            "publications": [],
        }
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to retrieve publication details: {e!s}",
            "accession": study_accession,
            "publication_count": 0,
            "publications": [],
        }
