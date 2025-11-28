# Developer Guide

## Project Overview

This is an MCP (Model Context Protocol) server that provides access to RNA sequencing datasets from the European Nucleotide Archive (ENA). The goal is to help researchers find publicly available bulk and single-cell RNA-seq datasets for validating hypotheses or reproducing published analyses.

## Architecture

**Framework**: FastMCP - provides the MCP server infrastructure and tool registration
**APIs Used**:
- ENA Portal API (`www.ebi.ac.uk/ena/portal/api`) - for searching studies and retrieving metadata
- ENA Browser API (`www.ebi.ac.uk/ena/browser/api`) - for detailed study summaries and publication links
- Europe PMC API (`www.ebi.ac.uk/europepmc/webservices/rest`) - for retrieving detailed publication metadata

**HTTP Client**: httpx (async)
**Data Validation**: Pydantic v2

## Code Organization

This is a standard Python package with `src/` layout. Tools are decorated with `@mcp.tool` and automatically registered. When testing wrapped tools, access the underlying function with `.fn` attribute.

The server exposes ~10 tools for searching studies, retrieving metadata, finding publications, and generating download scripts. Each tool follows ENA's controlled vocabularies for library strategies and sources.

## Key Concepts

**Study Accessions**: Projects have multiple formats (SRP/ERP/DRP or PRJNA/PRJEB/PRJDB). Both work interchangeably.

**Library Strategies**: 50+ types (RNA-Seq, ChIP-Seq, ATAC-seq, miRNA-Seq, etc.). Pre-defined presets exist for common use cases (bulk, single-cell, etc.).

**Publications**: Studies link to PubMed IDs via ENA Browser API. Europe PMC enriches this with full metadata including ORCID IDs, citations, and full-text links.

## Testing Philosophy

This project uses pytest with async support. Write clean, minimal tests with simple assertions. No verbose output, no boilerplate main functions. Test files live alongside source code and use proper package imports - never manipulate `sys.path`.

## Code Style

Production code should be clean and self-documenting. Avoid references to bugs, fixes, or workarounds in naming. Focus on what the code does, not its history. Follow established patterns in the codebase for consistency.
