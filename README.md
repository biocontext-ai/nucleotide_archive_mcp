# RNA Dataset Search - MCP Server

[![BioContextAI - Registry](https://img.shields.io/badge/Registry-package?style=flat&label=BioContextAI&labelColor=%23fff&color=%233555a1&link=https%3A%2F%2Fbiocontext.ai%2Fregistry)](https://biocontext.ai/registry)
[![Tests][badge-tests]][tests]
[![Documentation][badge-docs]][documentation]

[badge-tests]: https://img.shields.io/github/actions/workflow/status/biocontext-ai/nucleotide_archive_mcp/test.yaml?branch=main
[badge-docs]: https://img.shields.io/readthedocs/nucleotide_archive_mcp

A Model Context Protocol (MCP) server for searching and accessing RNA sequencing datasets from the [European Nucleotide Archive (ENA)](https://www.ebi.ac.uk/ena/browser/home). Find publicly available bulk RNA-seq and single-cell RNA-seq datasets to validate research hypotheses or reproduce published analyses.

**Optimized for**: Human and mouse disease-related RNA-seq studies with support for bulk, single-cell, and spatial transcriptomics.

## Features

- **Disease-Focused Search**: Find datasets by disease, organism, and tissue type
- **Advanced Technology Filtering**:
  - Simple presets: bulk, single-cell, small-rna, ribo-seq, rna-all
  - Granular control: Filter by 50+ library strategies (RNA-Seq, miRNA-Seq, ChIP-Seq, ATAC-seq, etc.)
  - Source filtering: TRANSCRIPTOMIC, GENOMIC, METAGENOMIC, etc.
- **Common Organism Names**: Use "human", "mouse", "rat" instead of scientific names
- **Download Support**: Generate wget/curl scripts for downloading FASTQ files
- **Study Metadata**: Retrieve comprehensive metadata including PubMed IDs
- **Publication Links**: Discover datasets associated with PubMed publications
- **Flexible Queries**: Build custom queries with multiple field conditions
- **Field Discovery**: Explore available search and return fields
- **Environment Configuration**: Customize API endpoints, timeouts, and logging via environment variables

## Available Tools

The MCP server provides 10 specialized tools:

### Search & Discovery
1. **search_rna_studies** - Unified search with preset filters or advanced library strategy/source filtering
2. **list_library_types** - List all 50+ available library strategies and sources
3. **get_study_details** - Get comprehensive metadata for a specific study (includes PubMed IDs)
4. **find_studies_by_publication** - Find studies associated with a PubMed ID
5. **search_studies_by_keywords** - Flexible keyword search across study titles

### Download & Access
6. **get_download_urls** - Get FTP download URLs for all data files in a study
7. **generate_download_script** - Generate bash scripts (wget/curl) for downloading data

### Advanced
8. **get_available_fields** - Discover searchable and returnable fields for different data types
9. **get_result_types** - List all available data types in ENA
10. **build_custom_query** - Construct advanced queries with multiple field conditions

## Example Use Cases

### Simple Searches (Preset Filters)
- Find human cancer bulk RNA-seq datasets: `disease="cancer"`
- Search for single-cell RNA-seq in mouse brain: `organism="mouse", tissue="brain", technology="single-cell"`
- Find small RNA sequencing studies: `technology="small-rna"`
- Ribosome profiling experiments: `technology="ribo-seq"`

### Advanced Searches (Specific Library Types)
- ChIP-Seq chromatin studies: `library_strategies=["ChIP-Seq"]`
- ATAC-seq accessibility data: `library_strategies=["ATAC-seq"]`
- Combined small RNA types: `library_strategies=["miRNA-Seq", "ncRNA-Seq"]`
- Any single-cell data: `library_sources=["TRANSCRIPTOMIC SINGLE CELL"]`
- Metagenomic RNA: `library_sources=["METATRANSCRIPTOMIC"]`

### Workflow Examples
- Download FASTQ files from a specific study
- Discover datasets from a specific publication
- Generate download scripts with MD5 verification
- List all available sequencing technologies: `list_library_types()`

## Getting started

Please refer to the [documentation][],
in particular, the [API documentation][].

You can also find the project on [BioContextAI](https://biocontext.ai), the community-hub for biomedical MCP servers: [nucleotide_archive_mcp on BioContextAI](https://biocontext.ai/registry/biocontext-ai/nucleotide_archive_mcp).

## Installation

You need to have Python 3.11 or newer installed on your system.
If you don't have Python installed, we recommend installing [uv][].

There are several alternative options to install nucleotide_archive_mcp:

### 1. Use `uvx` to run it immediately
After publication to PyPI:
```bash
uvx nucleotide_archive_mcp
```

Or from a Git repository:

```bash
uvx git+https://github.com/biocontext-ai/nucleotide_archive_mcp.git@main
```

### 2. Include it in one of various clients that supports the `mcp.json` standard

If your MCP server is published to PyPI, use the following configuration:

```json
{
  "mcpServers": {
    "nucleotide_archive_mcp": {
      "command": "uvx",
      "args": ["nucleotide_archive_mcp"]
    }
  }
}
```
In case the MCP server is not yet published to PyPI, use this configuration:

```json
{
  "mcpServers": {
    "nucleotide_archive_mcp": {
      "command": "uvx",
      "args": ["git+https://github.com/biocontext-ai/nucleotide_archive_mcp.git@main"]
    }
  }
}
```

For purely local development (e.g., in Cursor or VS Code), use the following configuration:

```json
{
  "mcpServers": {
    "nucleotide_archive_mcp": {
      "command": "uvx",
      "args": [
        "--refresh",
        "--from",
        "path/to/repository",
        "nucleotide_archive_mcp"
      ]
    }
  }
}
```

If you want to reuse and existing environment for local development, use the following configuration:

```json
{
  "mcpServers": {
    "nucleotide_archive_mcp": {
      "command": "uv",
      "args": ["run", "--directory", "path/to/repository", "nucleotide_archive_mcp"]
    }
  }
}
```

### 3. Install it through `pip`:

```bash
pip install --user nucleotide_archive_mcp
```

### 4. Install the latest development version:

```bash
pip install git+https://github.com/biocontext-ai/nucleotide_archive_mcp.git@main
```

## Configuration

The server can be configured via environment variables. Copy `.env.example` to `.env` and customize:

```bash
# ENA API Configuration
ENA_PORTAL_API_BASE=https://www.ebi.ac.uk/ena/portal/api  # Override API base URL
ENA_BROWSER_API_BASE=https://www.ebi.ac.uk/ena/browser/api
ENA_TIMEOUT=30.0                # Request timeout in seconds
ENA_SEARCH_LIMIT=20            # Default search result limit
ENA_MAX_RPS=10.0               # Rate limiting (requests per second)

# Logging
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

These settings allow you to:
- Use custom or mirror ENA API endpoints
- Adjust timeouts for slow connections
- Control default result limits
- Configure rate limiting for large batch operations
- Set logging verbosity for debugging

## Data Citation and Attribution

When using data from ENA in publications, please cite the data appropriately:

### How to Cite ENA Data

The top-level Project accession should be cited along with a link to the data in the ENA browser:

> "The data for this study have been deposited in the European Nucleotide Archive (ENA) at EMBL-EBI under accession number PRJEBxxxx (https://www.ebi.ac.uk/ena/browser/view/PRJEBxxxx)."

Replace `PRJEBxxxx` with the actual study accession number from your search results.

### Accessing Data in ENA Browser

All accessions can be viewed in the ENA browser:
- Direct URL: `https://www.ebi.ac.uk/ena/browser/view/<accession>`
- Example: https://www.ebi.ac.uk/ena/browser/view/PRJDB2345

### ORCID Data Claiming

ENA studies can be claimed against your ORCID ID through the [EBI Search interface](https://www.ebi.ac.uk/ebisearch/orcidclaimdocumentation.ebi). Search for your projects and click "Claim to ORCID" to link them to your ORCID profile.

## Data Policy and Usage

### ENA/INSDC Data Policy

This tool accesses data from the European Nucleotide Archive (ENA), which is part of the International Nucleotide Sequence Database Collaboration (INSDC) with DDBJ and GenBank.

**Key Points:**
- **Open Access**: All data in ENA/INSDC databases are freely and publicly accessible
- **No Restrictions**: Data have no use restrictions or licensing requirements
- **Redistribution**: Free redistribution and use of data is permitted
- **Permanence**: All submitted records remain permanently accessible
- **Attribution**: Proper citation of original submissions is expected (see above)

### Data Availability

Data in ENA can be:
- **Public**: Freely accessible through this tool and ENA browser
- **Confidential**: Pre-publication data not yet publicly available (not searchable through this tool)

Released data should be cited appropriately in publications and claimed via ORCID where applicable.

### Data Standards

ENA promotes data harmonization through:
- **Sample Checklists**: Minimum information standards for different data types
- **MIxS Standards**: Genomic Standards Consortium (GSC) minimum information standards
- **Community Standards**: Research community-developed reporting standards

For more information, see the [ENA Data Standards](https://ena-docs.readthedocs.io/en/latest/submit/general-guide/metadata.html) documentation.

## Disclaimer

This tool provides access to data from the European Nucleotide Archive (ENA) at EMBL-EBI. The tool is:
- **Independent**: Not officially affiliated with or endorsed by ENA, EMBL-EBI, or INSDC
- **Quality**: Data quality and accuracy are the responsibility of the original submitters
- **Updates**: ENA data and APIs may change; this tool is maintained to reflect current ENA services
- **Support**: For issues with ENA data or services, contact [ENA Support](https://www.ebi.ac.uk/ena/browser/support)

The European Nucleotide Archive is developed and maintained at EMBL-EBI under the guidance of the INSDC International Advisory Committee.

## Contact

If you found a bug with this MCP server, please use the [issue tracker][].

For questions about ENA data or services, contact [ENA Support](https://www.ebi.ac.uk/ena/browser/support).

## Acknowledgments

This tool accesses data from:
- **European Nucleotide Archive (ENA)** at EMBL-EBI
- **International Nucleotide Sequence Database Collaboration (INSDC)**

Special thanks to the ENA team for maintaining the public API and comprehensive documentation.

[uv]: https://github.com/astral-sh/uv
[issue tracker]: https://github.com/biocontext-ai/nucleotide_archive_mcp/issues
[tests]: https://github.com/biocontext-ai/nucleotide_archive_mcp/actions/workflows/test.yaml
[documentation]: https://nucleotide_archive_mcp.readthedocs.io
[changelog]: https://nucleotide_archive_mcp.readthedocs.io/en/latest/changelog.html
[api documentation]: https://nucleotide_archive_mcp.readthedocs.io/en/latest/api.html
[pypi]: https://pypi.org/project/nucleotide_archive_mcp
