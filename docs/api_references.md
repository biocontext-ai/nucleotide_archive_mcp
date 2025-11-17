# API Reference Documentation

This file contains important API documentation snippets for development reference.

## ENA Portal API

### Base URL
```
https://www.ebi.ac.uk/ena/portal/api
```

### Rate Limits
- **50 requests per second** maximum
- Recommended: No more than 10 concurrent searches

### Core Endpoints

#### `/search` - Search for records
- **Methods:** GET, POST
- **Parameters:**
  - `result` (required): Dataset type (e.g., `study`, `read_study`, `read_run`, `sample`, `analysis`)
  - `query` (required): Search query with logical operators (AND, OR, NOT)
  - `fields` (optional): Comma-separated list of return fields
  - `format` (optional): `tsv` (default) or `json`
  - `limit` (optional): Max records (default: 10, set to 0 for all)
  - `offset` (optional): Pagination offset
  - `dataPortal` (optional): `ena`, `faang`, `metagenome`, `pathogen`

**Example:**
```
GET /search?result=read_study&query=tax_tree(9606)%20AND%20library_strategy="RNA-Seq"&format=json&limit=20
```

#### `/count` - Count matching records
- Same parameters as `/search` but returns count only

#### `/searchFields` - Get available search fields
```
GET /searchFields?result=read_study
```

#### `/returnFields` - Get available return fields
```
GET /returnFields?result=read_study
```

#### `/results` - List available result types
```
GET /results?dataPortal=ena
```

#### `/filereport` - Get file information for accessions
- **Parameters:**
  - `accession` (required): Comma-separated accessions
  - `result` (required): Result type
  - `fields` (optional): File metadata fields

#### `/links/{dataType}` - Get related records
```
GET /links/study
```

### Query Syntax

- **Equality:** `field="value"` or `field=value`
- **Numeric ranges:** `field>=100 AND field<=1000`
- **Wildcards:** `description=*cancer*`
- **Taxonomy:** `tax_eq(9606)` (exact) or `tax_tree(9606)` (includes descendants)
- **Logical operators:** `AND`, `OR`, `NOT`
- **Grouping:** Use parentheses for complex queries

**Example queries:**
```
tax_tree(9606) AND library_strategy="RNA-Seq"
study_accession="PRJNA123456"
country="United Kingdom" AND collection_date>=2020
```

### Common Result Types

- `study` - Studies (projects)
- `read_study` - Raw read studies
- `sample` - Samples
- `read_run` - Individual sequencing runs
- `read_experiment` - Sequencing experiments
- `analysis` - Analyses
- `assembly` - Genome assemblies

### Important Fields

**Study-level:**
- `study_accession`, `secondary_study_accession`, `study_title`, `study_description`
- `study_alias`, `center_name`, `first_public`, `last_updated`
- `tax_id`, `scientific_name`
- `library_strategy`, `library_source`, `library_selection`

**Cross-references:**
- `pubmed_id` - PubMed publication ID
- `project_name`, `bioproject`

---

## HTTPX Documentation

### Basic Usage

```python
import httpx

# Synchronous
response = httpx.get('https://api.example.com/data')
response.status_code  # 200
response.json()  # Parse JSON response

# With query parameters
response = httpx.get('https://api.example.com/search', params={
    'query': 'RNA-Seq',
    'limit': 10
})

# Async client (recommended for MCP servers)
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get('https://api.example.com/data')
    data = response.json()
```

### Best Practices

1. **Use AsyncClient for async operations:**
   ```python
   async with httpx.AsyncClient() as client:
       response = await client.get(url)
   ```

2. **Set timeouts:**
   ```python
   client = httpx.AsyncClient(timeout=30.0)
   ```

3. **Handle errors:**
   ```python
   response.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx
   ```

4. **Headers:**
   ```python
   headers = {'User-Agent': 'MyApp/1.0'}
   response = await client.get(url, headers=headers)
   ```

---

## FastMCP Documentation

### Tool Definition

```python
from fastmcp import FastMCP

mcp = FastMCP("Server Name")

@mcp.tool
async def my_tool(param: str, count: int = 10) -> dict:
    """Tool description for the LLM.

    Parameters
    ----------
    param : str
        Description of parameter
    count : int, optional
        Number of results (default: 10)

    Returns
    -------
    dict
        Result data
    """
    return {"result": "data"}
```

### Key Principles

1. **Type hints are mandatory** - FastMCP generates schemas from them
2. **Docstrings become tool descriptions** - Use NumPy-style
3. **Async support** - Use `async def` for async operations
4. **Return JSON-serializable data** - Dicts, lists, strings, numbers

### Context for Logging

```python
from fastmcp import Context

@mcp.tool
async def tool_with_logging(query: str, ctx: Context) -> dict:
    await ctx.info(f"Processing query: {query}")
    # ... do work
    await ctx.info("Complete")
    return result
```

### Error Handling

Let exceptions propagate to provide feedback to the LLM:
```python
@mcp.tool
async def safe_tool(id: str) -> dict:
    if not id:
        raise ValueError("ID cannot be empty")
    # ... continue
```
