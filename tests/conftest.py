"""Shared test fixtures and configuration for RNA Dataset Search tests."""

import pytest
import pytest_asyncio
from fastmcp import Client

import nucleotide_archive_mcp

pytest_plugins = ("pytest_asyncio",)


@pytest_asyncio.fixture(scope="function")
async def mcp_client():
    """Create an MCP client for testing."""
    async with Client(nucleotide_archive_mcp.mcp) as client:
        yield client


@pytest.fixture
def sample_study_accession():
    """Return a known small study accession for testing."""
    return "PRJDB2345"
