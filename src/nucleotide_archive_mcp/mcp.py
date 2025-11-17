"""MCP server configuration for RNA Dataset Search."""

from fastmcp import FastMCP

mcp: FastMCP = FastMCP(
    name="nucleotide_archive_mcp",
    instructions="""This MCP server provides access to the European Nucleotide Archive (ENA)
to search for RNA sequencing datasets and studies.

Use this server to:
- Find publicly available RNA-seq datasets by organism, keywords, or library strategy
- Get detailed metadata about specific studies
- Discover datasets associated with publications (via PubMed ID)
- Search for studies related to specific research topics
- Explore available data types and searchable fields

The server focuses on study-level searches, which are ideal for finding datasets
to validate research hypotheses or reproduce published analyses. Studies typically
contain multiple samples and are often linked to publications.""",
    on_duplicate_tools="error",
)
