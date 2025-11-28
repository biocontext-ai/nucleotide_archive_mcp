"""Tool for getting detailed study information."""

from typing import Annotated, Any

import httpx
from pydantic import Field

from nucleotide_archive_mcp.config import DEFAULT_TIMEOUT, ENA_BROWSER_API_BASE
from nucleotide_archive_mcp.mcp import mcp

EUROPEPMC_API_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


@mcp.tool
async def get_study_details(
    study_accession: Annotated[
        str,
        Field(
            description="Study accession from search results. Accepts SRP/ERP/DRP or PRJNA/PRJEB/PRJDB formats",
            examples=["SRP417965", "PRJNA123456", "PRJEB12345"],
        ),
    ],
) -> dict:
    """Get comprehensive metadata for a specific ENA study including publications.

    Usage Tips
    ----------
    Call after search_rna_studies() to verify a study matches your research needs before downloading.
    Returns detailed study description, publication links, and institutional metadata. Use this to
    check publications array for PubMed IDs.

    Returns
    -------
    dict
        Dictionary containing:
        - accession: Study accession
        - title: Brief study title
        - description: Detailed study description (full abstract/methods)
        - publications: List of publications with pubmed_id and source
        - center_name: Submitting institution
        - alias: Submitter's study name (often GSE accession for GEO)
        - data_type: Usually "STUDY"
        - status: "public" or "private"
        - first_public: Date made public (YYYY-MM-DD)
        - last_updated: Last modification date (YYYY-MM-DD)
        - file_report_links: Direct API links for file reports
        - error: Error message if study not found or if request fails
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
    study_accession: Annotated[
        str,
        Field(
            description="Study accession from search results. Accepts SRP/ERP/DRP or PRJNA/PRJEB/PRJDB formats",
            examples=["SRP417965", "PRJNA802133", "PRJEB12345"],
        ),
    ],
) -> dict:
    """Get detailed publication information for a study from ENA and Europe PMC.

    Usage Tips
    ----------
    Call after search_rna_studies() to get full publication metadata including author ORCID IDs,
    affiliations, citation counts, and full-text links. Enriches basic publication info from
    get_study_details() with complete bibliographic data from Europe PMC.

    Returns
    -------
    dict
        Dictionary containing:
        - accession: Study accession
        - publication_count: Number of publications found
        - publications: List of detailed publication objects, each with:
            - pubmed_id: PubMed ID
            - pmcid: PubMed Central ID (if available)
            - doi: Digital Object Identifier (if available)
            - title: Publication title
            - authors: List of author names
            - first_author: First author name
            - last_author: Last author name
            - author_details: Detailed author info with ORCID and affiliations
            - journal: Journal name
            - journal_issn: Journal ISSN
            - publication_year: Year published
            - publication_date: Full publication date
            - abstract: Publication abstract
            - citation_count: Times cited
            - is_open_access: Whether open access
            - in_epmc: Whether in Europe PMC
            - in_pmc: Whether in PubMed Central
            - has_pdf: Whether PDF available
            - full_text_urls: Available full text links
        - error: Error message if any
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
