"""Basic integration tests for RNA Dataset Search MCP server."""

import pytest

import nucleotide_archive_mcp


def test_package_has_version():
    """Test that package version exists."""
    assert nucleotide_archive_mcp.__version__ is not None


@pytest.mark.asyncio
async def test_all_tools_registered(mcp_client):
    """Test that all expected MCP tools are registered and available."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    expected_tools = [
        "search_rna_studies",
        "get_study_details",
        "find_studies_by_publication",
        "search_studies_by_keywords",
        "get_available_fields",
        "get_result_types",
        "build_custom_query",
        "get_download_urls",
        "generate_download_script",
    ]

    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Tool {expected_tool} not found in registered tools"
