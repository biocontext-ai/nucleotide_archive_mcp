"""ENA Portal API client using httpx.

This module provides a high-level async client for interacting with the
European Nucleotide Archive (ENA) Portal API.
"""

from typing import Any

import httpx

from nucleotide_archive_mcp.config import DEFAULT_TIMEOUT, ENA_PORTAL_API_BASE


class ENAClient:
    """Async client for the ENA Portal API.

    This client provides methods for searching and retrieving data from the
    European Nucleotide Archive using their RESTful API.

    Attributes
    ----------
    base_url : str
        Base URL for the ENA Portal API
    timeout : float
        Request timeout in seconds
    """

    def __init__(self, base_url: str = ENA_PORTAL_API_BASE, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the ENA client.

        Parameters
        ----------
        base_url : str, optional
            Base URL for the ENA Portal API (default: from config)
        timeout : float, optional
            Request timeout in seconds (default: from config)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search(
        self,
        result: str,
        query: str,
        fields: str | None = None,
        limit: int = 20,
        format: str = "json",
        data_portal: str = "ena",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Search the ENA database.

        Note: The ENA Portal API does not support pagination with offset.
        To retrieve all results, use limit=0.

        Parameters
        ----------
        result : str
            Result type (e.g., 'study', 'read_study', 'sample', 'read_run')
        query : str
            Search query using ENA query syntax
        fields : str, optional
            Comma-separated list of fields to return
        limit : int, optional
            Maximum number of results (default: 20, use 0 for all)
        format : str, optional
            Response format: 'json' or 'tsv' (default: 'json')
        data_portal : str, optional
            Data portal: 'ena', 'faang', 'metagenome', 'pathogen' (default: 'ena')

        Returns
        -------
        dict or list[dict]
            Search results in JSON format

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        params = {
            "result": result,
            "query": query,
            "format": format,
            "limit": limit,
            "dataPortal": data_portal,
        }

        if fields:
            params["fields"] = fields

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/search", params=params)  # type: ignore[arg-type]
            response.raise_for_status()

            if format == "json":
                return response.json()  # type: ignore[no-any-return]
            return response.text  # type: ignore[return-value]

    async def count(
        self,
        result: str,
        query: str,
        data_portal: str = "ena",
    ) -> int:
        """Count records matching a query.

        Parameters
        ----------
        result : str
            Result type (e.g., 'study', 'read_study', 'sample')
        query : str
            Search query using ENA query syntax
        data_portal : str, optional
            Data portal (default: 'ena')

        Returns
        -------
        int
            Number of matching records

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        params = {
            "result": result,
            "query": query,
            "dataPortal": data_portal,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/count", params=params)
            response.raise_for_status()
            # ENA count endpoint returns "count\n<number>" format
            # We need to parse the number from the last line
            text = response.text.strip()
            if "\n" in text:
                # Split by newline and get the last line (the actual count)
                return int(text.split("\n")[-1])
            return int(text)

    async def get_search_fields(self, result: str) -> list[dict[str, Any]]:
        """Get available search fields for a result type.

        Parameters
        ----------
        result : str
            Result type (e.g., 'study', 'read_study')

        Returns
        -------
        list[dict]
            List of available search fields with metadata

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        params = {"result": result}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/searchFields", params=params)
            response.raise_for_status()

            # The searchFields endpoint returns TSV format, not JSON
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                return []

            headers = lines[0].split("\t")
            fields = []
            for line in lines[1:]:
                values = line.split("\t")
                if len(values) == len(headers):
                    fields.append(dict(zip(headers, values, strict=False)))

            return fields

    async def get_return_fields(self, result: str) -> list[dict[str, Any]]:
        """Get available return fields for a result type.

        Parameters
        ----------
        result : str
            Result type (e.g., 'study', 'read_study')

        Returns
        -------
        list[dict]
            List of available return fields with metadata

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        params = {"result": result}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/returnFields", params=params)
            response.raise_for_status()

            # The returnFields endpoint returns TSV format, not JSON
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                return []

            headers = lines[0].split("\t")
            fields = []
            for line in lines[1:]:
                values = line.split("\t")
                if len(values) == len(headers):
                    fields.append(dict(zip(headers, values, strict=False)))

            return fields

    async def get_results(self, data_portal: str = "ena") -> list[dict[str, Any]]:
        """Get available result types for a data portal.

        Parameters
        ----------
        data_portal : str, optional
            Data portal (default: 'ena')

        Returns
        -------
        list[dict]
            List of available result types

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        params = {"dataPortal": data_portal}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/results", params=params)
            response.raise_for_status()

            # The results endpoint returns TSV format, not JSON
            # Parse it into a list of dictionaries
            lines = response.text.strip().split("\n")
            if len(lines) < 2:
                return []

            # First line is the header
            headers = lines[0].split("\t")

            # Parse each data line
            results = []
            for line in lines[1:]:
                values = line.split("\t")
                if len(values) == len(headers):
                    result_dict = dict(zip(headers, values, strict=False))
                    results.append(result_dict)

            return results

    async def get_file_report(
        self,
        accessions: str | list[str],
        result: str,
        fields: str | None = None,
        format: str = "json",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Get file information for accessions.

        Parameters
        ----------
        accessions : str or list[str]
            Single accession or list of accessions
        result : str
            Result type
        fields : str, optional
            Comma-separated list of fields to return
        format : str, optional
            Response format: 'json' or 'tsv' (default: 'json')

        Returns
        -------
        dict or list[dict]
            File report data

        Raises
        ------
        httpx.HTTPStatusError
            If the API returns an error status code
        """
        if isinstance(accessions, list):
            accessions = ",".join(accessions)

        params = {
            "accession": accessions,
            "result": result,
            "format": format,
        }

        if fields:
            params["fields"] = fields

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/filereport", params=params)
            response.raise_for_status()

            if format == "json":
                return response.json()  # type: ignore[no-any-return]
            return response.text  # type: ignore[return-value]
