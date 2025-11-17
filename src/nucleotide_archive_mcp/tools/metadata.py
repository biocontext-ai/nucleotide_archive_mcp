"""Tools for discovering available fields and metadata."""

from typing import Any

import httpx

from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp


@mcp.tool
async def get_available_fields(
    result_type: str = "read_study",
    field_category: str = "all",
) -> dict:
    """Get available search and return fields for an ENA result type.

    This tool helps you discover what fields you can search on and what
    metadata fields are available for a given data type in ENA.

    Parameters
    ----------
    result_type : str, optional
        Type of data to query. Common options:
        - "read_study": RNA-seq studies (default, recommended)
        - "study": All studies
        - "sample": Sample records
        - "read_run": Individual sequencing runs
        - "read_experiment": Sequencing experiments
        - "analysis": Analysis records
    field_category : str, optional
        Which fields to return:
        - "all": Both search and return fields (default)
        - "search": Only searchable fields
        - "return": Only returnable fields

    Returns
    -------
    dict
        Dictionary containing:
        - result_type: The queried result type
        - search_fields: List of searchable fields (if requested)
        - return_fields: List of returnable fields (if requested)

    Examples
    --------
    Get all fields for RNA-seq studies:
        result_type="read_study"

    Get only searchable fields for samples:
        result_type="sample", field_category="search"
    """
    client = ENAClient()

    response: dict[str, Any] = {"result_type": result_type}

    try:
        if field_category in ("all", "search"):
            search_fields = await client.get_search_fields(result_type)
            # Format for better readability
            # Note: TSV fields use "columnId" not "fieldId"
            response["search_fields"] = [
                {
                    "id": field.get("columnId", ""),
                    "description": field.get("description", ""),
                    "type": field.get("type", ""),
                }
                for field in search_fields
            ]
            response["search_fields_count"] = len(search_fields)

        if field_category in ("all", "return"):
            return_fields = await client.get_return_fields(result_type)
            # Format for better readability
            # Note: TSV fields use "columnId" not "fieldId"
            response["return_fields"] = [
                {
                    "id": field.get("columnId", ""),
                    "description": field.get("description", ""),
                    "type": field.get("type", ""),
                }
                for field in return_fields
            ]
            response["return_fields_count"] = len(return_fields)

        return response

    except (httpx.HTTPError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to retrieve fields: {e!s}",
            "result_type": result_type,
        }


@mcp.tool
async def get_result_types() -> dict:
    """Get all available result types (data categories) in ENA.

    This tool shows what types of data you can search for in the
    European Nucleotide Archive.

    Returns
    -------
    dict
        Dictionary containing:
        - count: Number of available result types
        - result_types: List of result types with descriptions

    Examples
    --------
    Discover what data types are available:
        (no parameters needed)
    """
    client = ENAClient()

    try:
        results = await client.get_results(data_portal="ena")

        # Format for readability
        # Note: TSV fields are resultId, description, primaryAccessionType, recordCount, lastUpdated
        formatted_results = [
            {
                "id": result.get("resultId", ""),
                "description": result.get("description", ""),
                "primaryAccessionType": result.get("primaryAccessionType", ""),
                "recordCount": result.get("recordCount", ""),
                "lastUpdated": result.get("lastUpdated", ""),
            }
            for result in results
        ]

        return {
            "count": len(formatted_results),
            "result_types": formatted_results,
            "recommended_for_rna_studies": ["read_study", "study"],
        }

    except (httpx.HTTPError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to retrieve result types: {e!s}",
            "count": 0,
            "result_types": [],
        }


@mcp.tool
async def build_custom_query(
    field_conditions: list[dict[str, str]],
    operator: str = "AND",
) -> dict:
    """Build a custom ENA query from field conditions.

    This advanced tool helps construct complex queries by combining multiple
    field conditions with logical operators. Useful for precise filtering.

    Parameters
    ----------
    field_conditions : list[dict]
        List of conditions, each with keys:
        - "field": Field name (e.g., "tax_id", "library_strategy")
        - "operator": Comparison operator ("=", ">=", "<=", "!=", or "contains")
        - "value": Value to compare
    operator : str, optional
        Logical operator to combine conditions: "AND" or "OR" (default: "AND")

    Returns
    -------
    dict
        Dictionary containing:
        - query: The constructed ENA query string
        - field_count: Number of conditions
        - example_usage: How to use this query

    Examples
    --------
    Build a query for human RNA-seq studies after 2020:
        field_conditions=[
            {"field": "tax_id", "operator": "=", "value": "9606"},
            {"field": "library_strategy", "operator": "=", "value": "RNA-Seq"},
            {"field": "first_public", "operator": ">=", "value": "2020-01-01"}
        ]

    Find studies with specific keywords:
        field_conditions=[
            {"field": "study_title", "operator": "contains", "value": "cancer"},
            {"field": "study_description", "operator": "contains", "value": "treatment"}
        ],
        operator="OR"
    """
    if not field_conditions:
        return {
            "error": "At least one field condition is required",
            "query": None,
        }

    query_parts = []

    for condition in field_conditions:
        field = condition.get("field", "")
        op = condition.get("operator", "=")
        value = condition.get("value", "")

        if not field or not value:
            continue

        if op == "contains":
            # Wildcard search
            query_parts.append(f"{field}=*{value}*")
        elif op in ("=", "!=", ">=", "<=", ">", "<"):
            # Quote values for exact matching
            if op == "=":
                query_parts.append(f'{field}="{value}"')
            else:
                query_parts.append(f"{field}{op}{value}")
        else:
            # Default to equality
            query_parts.append(f'{field}="{value}"')

    if not query_parts:
        return {
            "error": "No valid conditions provided",
            "query": None,
        }

    # Join with the specified operator
    query = f" {operator} ".join(query_parts)

    return {
        "query": query,
        "field_count": len(query_parts),
        "operator": operator,
        "example_usage": f'Use this query with search_rna_studies or other search tools by passing query="{query}"',
    }
