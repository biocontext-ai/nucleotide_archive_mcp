"""Test multi-word search functionality.

This test verifies that the fix for multi-word disease/keyword searches works correctly.
The ENA Portal API doesn't support wildcards in multi-word phrases, so we split them
into individual words and search for each.
"""

import pytest


@pytest.mark.asyncio
async def test_fabry_nephropathy_search(mcp_client):
    """Test that 'Fabry nephropathy' finds SRP342347/PRJNA773084.

    This is a regression test for the issue where multi-word disease searches
    returned no results because the API doesn't support wildcards in multi-word phrases.
    """
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "Fabry nephropathy",
            "organism": "Homo sapiens",
            "technology": "bulk",
            "limit": 10,
        },
    )

    data = result.data

    # Should find at least one study
    assert data["count"] > 0, "Should find Fabry nephropathy studies"
    assert data["returned"] > 0, "Should return Fabry nephropathy studies"

    # Should find the specific study SRP342347/PRJNA773084
    study_accessions = [s.get("study_accession") for s in data["studies"]]
    secondary_accessions = [s.get("secondary_study_accession") for s in data["studies"]]

    assert "PRJNA773084" in study_accessions or "SRP342347" in secondary_accessions, (
        "Should find the Fabry nephropathy study (PRJNA773084/SRP342347)"
    )

    # Verify the query was constructed correctly with split words
    assert "Fabry" in data["query_used"]
    assert "nephropathy" in data["query_used"]


@pytest.mark.asyncio
async def test_single_word_disease_search(mcp_client):
    """Test that single-word disease searches still work."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "cancer",
            "organism": "Homo sapiens",
            "technology": "bulk",
            "limit": 5,
        },
    )

    data = result.data

    # Should find cancer studies
    assert data["count"] > 0, "Should find cancer studies"
    assert 'study_title="*cancer*"' in data["query_used"]


@pytest.mark.asyncio
async def test_multiword_phrase_with_common_words(mcp_client):
    """Test that multi-word phrases with common words like 'in' work correctly."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "Podocyte injury in Fabry nephropathy",
            "organism": "Homo sapiens",
            "technology": "bulk",
            "limit": 10,
        },
    )

    data = result.data

    # Should still find the study even with 5+ words including "in"
    assert data["count"] > 0, "Should find studies even with long multi-word phrases"

    # Verify all words are in the query
    query = data["query_used"]
    assert "Podocyte" in query
    assert "injury" in query
    assert "in" in query
    assert "Fabry" in query
    assert "nephropathy" in query
