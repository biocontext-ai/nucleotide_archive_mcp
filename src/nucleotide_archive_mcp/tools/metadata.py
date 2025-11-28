"""Tools for discovering available fields and metadata."""

from typing import Annotated, Any

import httpx
from pydantic import Field

from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp


@mcp.tool
async def get_available_fields(
    result_type: Annotated[
        str,
        Field(
            description="Type of ENA data to query (read_study, study, sample, read_run, read_experiment, analysis)",
            examples=["read_study", "sample", "read_run"],
        ),
    ] = "read_study",
    field_category: Annotated[
        str,
        Field(
            description="Which fields to return (all, search, return)",
            examples=["all", "search", "return"],
        ),
    ] = "all",
) -> dict:
    """Get available search and return fields for an ENA result type.

    Usage Tips
    ----------
    Use to discover what fields you can search on and what metadata fields are available
    for a given data type in ENA. Helpful for building custom queries with build_custom_query().

    Returns
    -------
    dict
        Dictionary containing:
        - result_type: The queried result type
        - search_fields: List of searchable fields with id, description, type (if requested)
        - search_fields_count: Number of search fields (if requested)
        - return_fields: List of returnable fields with id, description, type (if requested)
        - return_fields_count: Number of return fields (if requested)
        - error: Error message if any
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

    Usage Tips
    ----------
    Use to discover what types of data you can search for in the European Nucleotide Archive.
    Most users will use read_study or study for RNA-seq searches.

    Returns
    -------
    dict
        Dictionary containing:
        - count: Number of available result types
        - result_types: List of result types with id, description, primaryAccessionType, recordCount, lastUpdated
        - recommended_for_rna_studies: Recommended types for RNA studies
        - error: Error message if any
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
    field_conditions: Annotated[
        list[dict[str, str]],
        Field(
            description='List of conditions, each with "field", "operator" (=, >=, <=, !=, contains), and "value"',
            examples=[
                [
                    {"field": "tax_id", "operator": "=", "value": "9606"},
                    {"field": "library_strategy", "operator": "=", "value": "RNA-Seq"},
                ]
            ],
        ),
    ],
    operator: Annotated[
        str,
        Field(
            description="Logical operator to combine conditions (AND or OR)",
            examples=["AND", "OR"],
        ),
    ] = "AND",
) -> dict:
    """Build a custom ENA query from field conditions.

    Usage Tips
    ----------
    Advanced tool for constructing complex queries by combining multiple field conditions with
    logical operators. Use for precise filtering beyond what search_rna_studies() offers.
    Call get_available_fields() first to discover searchable field names.

    Returns
    -------
    dict
        Dictionary containing:
        - query: The constructed ENA query string
        - field_count: Number of conditions used
        - operator: Logical operator used
        - example_usage: How to use this query with other tools
        - error: Error message if any
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
