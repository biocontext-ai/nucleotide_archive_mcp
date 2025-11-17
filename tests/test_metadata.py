"""Tests for metadata and field discovery functionality.

Tests focus on:
- Discovering available result types
- Getting searchable and returnable fields
- Building custom queries
- High-level metadata operations
"""

import pytest


@pytest.mark.asyncio
async def test_get_result_types(mcp_client):
    """Test discovering available ENA result types."""
    result = await mcp_client.call_tool("get_result_types", {})

    data = result.data
    assert data["count"] > 0, "Should find multiple result types"
    assert isinstance(data["result_types"], list)

    # Verify we have study-related result types
    result_ids = [rt["id"] for rt in data["result_types"]]
    assert "read_study" in result_ids or "study" in result_ids, "Should include study result types"


@pytest.mark.asyncio
async def test_get_result_types_structure(mcp_client):
    """Test that result types have expected metadata fields."""
    result = await mcp_client.call_tool("get_result_types", {})

    data = result.data
    if data["result_types"]:
        result_type = data["result_types"][0]
        # Each result type should have these fields
        assert "id" in result_type
        assert "description" in result_type
        assert "recordCount" in result_type or "primaryAccessionType" in result_type


@pytest.mark.asyncio
async def test_get_available_fields_search(mcp_client):
    """Test getting searchable fields for read_study result type."""
    result = await mcp_client.call_tool(
        "get_available_fields",
        {
            "result_type": "read_study",
            "field_category": "search",
        },
    )

    data = result.data
    assert data["result_type"] == "read_study"
    assert "search_fields" in data
    assert data["search_fields_count"] > 0, "Should have searchable fields"

    # Verify common searchable fields exist
    field_ids = [f["id"] for f in data["search_fields"]]
    assert "study_title" in field_ids, "Should have study_title field"
    assert "library_strategy" in field_ids, "Should have library_strategy field"


@pytest.mark.asyncio
async def test_get_available_fields_return(mcp_client):
    """Test getting returnable fields for read_study result type."""
    result = await mcp_client.call_tool(
        "get_available_fields",
        {
            "result_type": "read_study",
            "field_category": "return",
        },
    )

    data = result.data
    assert "return_fields" in data
    assert data["return_fields_count"] > 0, "Should have returnable fields"

    # Verify common returnable fields
    field_ids = [f["id"] for f in data["return_fields"]]
    assert "study_accession" in field_ids, "Should have study_accession field"


@pytest.mark.asyncio
async def test_get_available_fields_all(mcp_client):
    """Test getting both search and return fields."""
    result = await mcp_client.call_tool(
        "get_available_fields",
        {
            "result_type": "read_study",
            "field_category": "all",
        },
    )

    data = result.data
    assert "search_fields" in data
    assert "return_fields" in data
    assert data["search_fields_count"] > 0
    assert data["return_fields_count"] > 0


@pytest.mark.asyncio
async def test_build_custom_query_simple(mcp_client):
    """Test building a simple custom query with one condition."""
    result = await mcp_client.call_tool(
        "build_custom_query",
        {
            "field_conditions": [
                {"field": "tax_id", "operator": "=", "value": "9606"},
            ],
            "operator": "AND",
        },
    )

    data = result.data
    assert "query" in data
    assert data["field_count"] == 1
    assert "tax_id" in data["query"]
    assert "9606" in data["query"]


@pytest.mark.asyncio
async def test_build_custom_query_multiple_conditions(mcp_client):
    """Test building a query with multiple conditions."""
    result = await mcp_client.call_tool(
        "build_custom_query",
        {
            "field_conditions": [
                {"field": "tax_id", "operator": "=", "value": "9606"},
                {"field": "library_strategy", "operator": "=", "value": "RNA-Seq"},
                {"field": "first_public", "operator": ">=", "value": "2020-01-01"},
            ],
            "operator": "AND",
        },
    )

    data = result.data
    assert data["field_count"] == 3
    query = data["query"]
    assert "tax_id" in query
    assert "library_strategy" in query
    assert "first_public" in query
    assert "AND" in query


@pytest.mark.asyncio
async def test_build_custom_query_or_operator(mcp_client):
    """Test building a query with OR operator."""
    result = await mcp_client.call_tool(
        "build_custom_query",
        {
            "field_conditions": [
                {"field": "study_title", "operator": "contains", "value": "cancer"},
                {"field": "study_title", "operator": "contains", "value": "tumor"},
            ],
            "operator": "OR",
        },
    )

    data = result.data
    assert data["operator"] == "OR"
    assert "OR" in data["query"]


@pytest.mark.asyncio
async def test_build_custom_query_contains_operator(mcp_client):
    """Test wildcard search with 'contains' operator."""
    result = await mcp_client.call_tool(
        "build_custom_query",
        {
            "field_conditions": [
                {"field": "study_title", "operator": "contains", "value": "brain"},
            ],
        },
    )

    data = result.data
    query = data["query"]
    # Contains should use wildcards
    assert "*brain*" in query or "brain" in query


@pytest.mark.asyncio
async def test_get_study_details(mcp_client, sample_study_accession):
    """Test getting detailed metadata for a specific study using Browser API."""
    result = await mcp_client.call_tool(
        "get_study_details",
        {"study_accession": sample_study_accession},
    )

    data = result.data
    assert "accession" in data
    assert data["accession"] == sample_study_accession
    assert "title" in data
    assert "description" in data
    assert "error" in data and data["error"] is None

    # Should have rich metadata from Browser API
    assert "center_name" in data
    assert "status" in data
    assert "first_public" in data or "last_updated" in data

    # Publications array should exist (may be empty)
    assert "publications" in data
    assert isinstance(data["publications"], list)
