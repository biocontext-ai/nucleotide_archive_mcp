"""Test suite for study publication retrieval functions."""

import pytest

from nucleotide_archive_mcp.tools.study_details import get_study_details, get_study_publications


@pytest.mark.asyncio
async def test_study_details():
    """Test get_study_details extracts PubMed IDs."""
    result = await get_study_details.fn("PRJNA802133")

    assert result["accession"] == "PRJNA802133"
    assert result["error"] is None
    assert len(result["publications"]) == 1
    assert result["publications"][0]["pubmed_id"] == "35947676"
    assert result["publications"][0]["source"] == "PubMed"


@pytest.mark.asyncio
async def test_study_publications():
    """Test get_study_publications retrieves Europe PMC metadata."""
    result = await get_study_publications.fn("PRJNA802133")

    assert result["accession"] == "PRJNA802133"
    assert result["error"] is None
    assert result["publication_count"] == 1

    pub = result["publications"][0]
    assert pub["pubmed_id"] == "35947676"
    assert pub["doi"] == "10.1126/scitranslmed.abg3277"
    assert pub["journal"] == "Science translational medicine"
    assert pub["publication_year"] == 2022
    assert len(pub["authors"]) == 26
    assert pub["citation_count"] > 0
    assert len(pub["author_details"]) == 26
    assert sum(1 for a in pub["author_details"] if a.get("orcid")) > 0
