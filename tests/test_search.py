"""Tests for RNA-seq study search functionality.

Tests focus on high-level search behavior and real-world use cases:
- Disease-based searches (main use case)
- Organism filtering (human/mouse)
- Technology filtering (bulk/single-cell)
- Tissue filtering
- Edge cases and error handling
"""

import pytest


@pytest.mark.asyncio
async def test_search_human_cancer_default(mcp_client):
    """Test default use case: searching for human cancer RNA-seq studies."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {"disease": "cancer", "limit": 5},
    )

    data = result.data
    assert data["count"] > 0, "Should find cancer studies"
    assert data["filters"]["organism"] == "Homo sapiens", "Default organism should be human"
    assert data["filters"]["technology"] == "bulk", "Default technology should be bulk RNA-seq"
    assert data["filters"]["disease"] == "cancer"
    assert len(data["studies"]) <= 5, "Should respect limit parameter"


@pytest.mark.asyncio
async def test_search_mouse_diabetes(mcp_client):
    """Test searching for mouse diabetes studies - common model organism use case."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "diabetes",
            "organism": "Mus musculus",
            "limit": 3,
        },
    )

    data = result.data
    assert data["filters"]["organism"] == "Mus musculus"
    assert data["filters"]["disease"] == "diabetes"
    assert "count" in data
    assert isinstance(data["studies"], list)


@pytest.mark.asyncio
async def test_search_single_cell_cancer(mcp_client):
    """Test single-cell technology filtering for cancer studies."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "cancer",
            "technology": "single-cell",
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["technology"] == "single-cell"
    assert "count" in data

    # Verify returned studies match technology filter
    if data["studies"]:
        assert any(
            "SINGLE CELL" in study.get("library_source", "") or "snRNA" in study.get("library_strategy", "")
            for study in data["studies"]
        ), "Results should include single-cell studies"


@pytest.mark.asyncio
async def test_search_bulk_rna_seq(mcp_client):
    """Test explicit bulk RNA-seq technology filtering."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "Alzheimer",
            "technology": "bulk",
            "limit": 3,
        },
    )

    data = result.data
    assert data["filters"]["technology"] == "bulk"
    assert "count" in data


@pytest.mark.asyncio
async def test_search_with_tissue_filter(mcp_client):
    """Test tissue-specific filtering for brain studies."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "tissue": "brain",
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["tissue"] == "brain"
    assert "count" in data
    assert isinstance(data["studies"], list)


@pytest.mark.asyncio
async def test_search_combined_filters(mcp_client):
    """Test combining multiple filters: disease + tissue + technology."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "cancer",
            "tissue": "liver",
            "technology": "rna-all",  # All RNA technologies
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["disease"] == "cancer"
    assert data["filters"]["tissue"] == "liver"
    assert data["filters"]["technology"] == "rna-all"
    assert "count" in data


@pytest.mark.asyncio
async def test_search_no_disease_filter(mcp_client):
    """Test searching without disease filter returns all organism studies."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "organism": "Saccharomyces cerevisiae",  # Yeast
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["organism"] == "Saccharomyces cerevisiae"
    assert data["filters"]["disease"] is None
    assert "count" in data
    assert data["count"] > 0, "Should find studies even without disease filter"


@pytest.mark.asyncio
async def test_search_all_rna_technologies(mcp_client):
    """Test 'rna-all' technology option includes various RNA-seq types."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "cancer",
            "technology": "rna-all",
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["technology"] == "rna-all"
    assert "count" in data


@pytest.mark.asyncio
async def test_search_cardiovascular_disease(mcp_client):
    """Test searching for cardiovascular disease - real-world medical use case."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "disease": "cardiovascular",
            "organism": "Homo sapiens",
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["disease"] == "cardiovascular"
    assert "count" in data


@pytest.mark.asyncio
async def test_search_returns_study_metadata(mcp_client):
    """Test that search returns essential study metadata fields."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {"disease": "cancer", "limit": 1},
    )

    data = result.data
    if data["studies"]:
        study = data["studies"][0]
        # Verify essential metadata is present
        assert "study_accession" in study
        assert "study_title" in study
        assert "library_strategy" in study
        assert "library_source" in study


@pytest.mark.asyncio
async def test_search_keyword_based(mcp_client):
    """Test keyword-based search across study titles."""
    result = await mcp_client.call_tool(
        "search_studies_by_keywords",
        {
            "keywords": "yeast",
            "limit": 5,
        },
    )

    data = result.data
    assert data["count"] > 0
    assert data["keywords_used"] == "yeast"
    assert isinstance(data["studies"], list)


@pytest.mark.asyncio
async def test_search_by_publication(mcp_client):
    """Test that pubmed search returns appropriate error message."""
    # PubMed ID search is not supported by ENA Portal API
    result = await mcp_client.call_tool(
        "find_studies_by_publication",
        {"pubmed_id": "33247152"},
    )

    data = result.data
    assert "error" in data
    assert "not supported" in data["error"].lower()
    assert data["count"] == 0
    assert data["studies"] == []
    assert "pubmed_id" in data
    assert data["pubmed_id"] == "33247152"
    assert isinstance(data["studies"], list)


@pytest.mark.asyncio
async def test_search_pagination(mcp_client):
    """Test that limit parameter works correctly.

    Note: ENA Portal API doesn't support offset-based pagination.
    To get all results, use limit=0.
    """
    # Test with small limit
    result1 = await mcp_client.call_tool(
        "search_rna_studies",
        {"disease": "cancer", "limit": 2},
    )

    # Test with slightly larger limit
    result2 = await mcp_client.call_tool(
        "search_rna_studies",
        {"disease": "cancer", "limit": 5},
    )

    data1 = result1.data
    data2 = result2.data

    # First result should have at most 2 studies
    assert len(data1["studies"]) <= 2

    # Second result should have more studies (or same if total < 5)
    assert len(data2["studies"]) >= len(data1["studies"])
    assert len(data2["studies"]) <= 5


@pytest.mark.asyncio
async def test_search_with_library_strategies(mcp_client):
    """Test advanced search with specific library strategies."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "library_strategies": ["RNA-Seq"],
            "technology": None,
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["library_strategies"] == ["RNA-Seq"]
    assert data["filters"]["technology"] is None
    assert "count" in data
    if data["studies"]:
        for study in data["studies"]:
            assert study.get("library_strategy") == "RNA-Seq"


@pytest.mark.asyncio
async def test_search_with_multiple_strategies(mcp_client):
    """Test filtering by multiple library strategies (miRNA + ncRNA)."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "library_strategies": ["miRNA-Seq", "ncRNA-Seq"],
            "technology": None,
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["library_strategies"] == ["miRNA-Seq", "ncRNA-Seq"]
    assert "count" in data


@pytest.mark.asyncio
async def test_search_with_library_sources(mcp_client):
    """Test filtering by specific library source."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "library_sources": ["TRANSCRIPTOMIC SINGLE CELL"],
            "technology": None,
            "limit": 5,
        },
    )

    data = result.data
    assert data["filters"]["library_sources"] == ["TRANSCRIPTOMIC SINGLE CELL"]
    assert "count" in data
    if data["studies"]:
        for study in data["studies"]:
            assert "SINGLE CELL" in study.get("library_source", "")


@pytest.mark.asyncio
async def test_search_invalid_library_strategy(mcp_client):
    """Test that invalid library strategy returns error."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "library_strategies": ["InvalidStrategy"],
            "technology": None,
            "limit": 5,
        },
    )

    data = result.data
    assert "error" in data
    assert "Invalid library strategies" in data["error"]
    assert data["count"] == 0
    assert data["studies"] == []


@pytest.mark.asyncio
async def test_list_library_types(mcp_client):
    """Test listing all available library types."""
    result = await mcp_client.call_tool("list_library_types", {})

    data = result.data
    assert "library_strategies" in data
    assert "library_sources" in data
    assert "rna_strategies" in data
    assert "summary" in data

    # Verify we have strategies and sources
    assert len(data["library_strategies"]) > 0
    assert len(data["library_sources"]) > 0
    assert len(data["rna_strategies"]) > 0

    # Check that RNA-Seq is in the strategies
    strategy_values = [s["value"] for s in data["library_strategies"]]
    assert "RNA-Seq" in strategy_values
    assert "miRNA-Seq" in strategy_values
    assert "Ribo-Seq" in strategy_values

    # Check sources
    source_values = [s["value"] for s in data["library_sources"]]
    assert "TRANSCRIPTOMIC" in source_values
    assert "TRANSCRIPTOMIC SINGLE CELL" in source_values


@pytest.mark.asyncio
async def test_common_organism_names(mcp_client):
    """Test that common organism names are mapped to scientific names."""
    result = await mcp_client.call_tool(
        "search_rna_studies",
        {
            "organism": "human",
            "limit": 1,
        },
    )

    data = result.data
    assert data["filters"]["organism"] == "Homo sapiens", "Common name 'human' should map to scientific name"
