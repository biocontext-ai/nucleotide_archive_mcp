"""Tools for downloading RNA-seq data from ENA."""

from pathlib import Path
from typing import Annotated

import httpx
from pydantic import Field

from nucleotide_archive_mcp.ena_client import ENAClient
from nucleotide_archive_mcp.mcp import mcp


async def _fetch_download_urls(
    study_accession: str,
    file_format: str = "fastq",
    include_md5: bool = True,
) -> dict:
    """Internal helper to fetch download URLs (not exposed as MCP tool)."""
    client = ENAClient()

    # Build fields list based on file format
    if file_format == "fastq":
        url_field = "fastq_ftp"
        md5_field = "fastq_md5"
        bytes_field = "fastq_bytes"
    elif file_format == "submitted":
        url_field = "submitted_ftp"
        md5_field = "submitted_md5"
        bytes_field = "submitted_bytes"
    elif file_format == "sra":
        url_field = "sra_ftp"
        md5_field = "sra_md5"
        bytes_field = "sra_bytes"
    else:
        return {
            "error": f"Unknown file format: {file_format}. Use 'fastq', 'submitted', or 'sra'",
            "study_accession": study_accession,
        }

    fields = f"run_accession,{url_field},{bytes_field}"
    if include_md5:
        fields += f",{md5_field}"

    try:
        # Get file report for all runs in the study
        results = await client.get_file_report(
            accessions=study_accession,
            result="read_run",
            fields=fields,
        )

        if not results:
            return {
                "study_accession": study_accession,
                "file_count": 0,
                "total_size_gb": 0,
                "runs": [],
                "message": "No files found for this study",
            }

        # Process results
        runs = []
        total_bytes = 0

        for run in results if isinstance(results, list) else [results]:
            run_accession = run.get("run_accession", "")
            urls = run.get(url_field, "")
            bytes_str = run.get(bytes_field, "")
            md5s = run.get(md5_field, "") if include_md5 else ""

            # Split semicolon-separated values (for paired-end reads)
            url_list = urls.split(";") if urls else []
            bytes_list = bytes_str.split(";") if bytes_str else []
            md5_list = md5s.split(";") if md5s else []

            # Calculate run size
            run_bytes = sum(int(b) for b in bytes_list if b)
            total_bytes += run_bytes

            # Format URLs with ftp:// prefix
            formatted_urls = [f"ftp://{url}" if not url.startswith("ftp://") else url for url in url_list]

            run_info = {
                "run_accession": run_accession,
                "file_count": len(url_list),
                "size_gb": round(run_bytes / 1e9, 2),
                "urls": formatted_urls,
            }

            if include_md5:
                run_info["md5_checksums"] = md5_list

            runs.append(run_info)

        return {
            "study_accession": study_accession,
            "file_count": sum(r["file_count"] for r in runs),
            "total_size_gb": round(total_bytes / 1e9, 2),
            "runs": runs,
        }

    except (httpx.HTTPError, ValueError, KeyError) as e:
        return {
            "error": f"Failed to retrieve download URLs: {e!s}",
            "study_accession": study_accession,
        }


@mcp.tool
async def get_download_urls(
    study_accession: Annotated[
        str,
        Field(
            description="Study accession from search results. Accepts SRP/ERP/DRP or PRJNA/PRJEB/PRJDB formats",
            examples=["PRJDB2345", "PRJNA123456", "SRP417965"],
        ),
    ],
    file_format: Annotated[
        str,
        Field(
            description="File format to download (fastq, submitted, or sra). FASTQ is most common",
            examples=["fastq", "submitted", "sra"],
        ),
    ] = "fastq",
    include_md5: Annotated[
        bool,
        Field(
            description="Include MD5 checksums for file integrity verification",
        ),
    ] = True,
) -> dict:
    """Get FTP download URLs for all sequencing data files in a study.

    Usage Tips
    ----------
    Call after search_rna_studies() to get download URLs for selected studies. Returns FTP URLs
    that can be used with wget/curl or passed to generate_download_script().

    Returns
    -------
    dict
        Dictionary containing:
        - study_accession: Queried study
        - file_count: Total number of files
        - total_size_gb: Total download size in GB
        - runs: List of per-run file info, each with:
            - run_accession: Run identifier
            - file_count: Files in this run (2 for paired-end)
            - size_gb: Run size in GB
            - urls: List of FTP URLs (ftp://...)
            - md5_checksums: List of MD5 hashes (if include_md5=True)
        - message: Info message if no files found
        - error: Error message if any
    """
    return await _fetch_download_urls(study_accession, file_format, include_md5)


@mcp.tool
async def generate_download_script(
    study_accession: Annotated[
        str,
        Field(
            description="Study accession from search results. Accepts SRP/ERP/DRP or PRJNA/PRJEB/PRJDB formats",
            examples=["PRJDB2345", "SRP417965", "PRJNA123456"],
        ),
    ],
    output_path: Annotated[
        str | None,
        Field(
            description="File path to save script (e.g., './download.sh'). If None, returns script content without saving. Script will be made executable (chmod 755)",
            examples=["./download.sh", "./download_study.sh", None],
        ),
    ] = None,
    script_type: Annotated[
        str,
        Field(
            description="Download tool to use (wget or curl). wget is recommended for resumable downloads with -nc flag",
            examples=["wget", "curl"],
        ),
    ] = "wget",
    file_format: Annotated[
        str,
        Field(
            description="File format to download (fastq, submitted, or sra). FASTQ is most common",
            examples=["fastq", "submitted", "sra"],
        ),
    ] = "fastq",
) -> dict:
    """Generate executable bash script to download all study data files.

    Usage Tips
    ----------
    After identifying interesting studies, generate a download script for the user to execute.
    Returns script content and optionally saves to file. Script includes MD5 verification commands.
    Typical workflow: search_rna_studies() → get_study_details() → generate_download_script().

    Returns
    -------
    dict
        Dictionary containing:
        - study_accession: Queried study
        - script_content: Complete bash script ready to execute
        - file_count: Number of files the script will download
        - total_size_gb: Total download size in GB
        - script_path: Save location (if output_path provided)
        - message: Success message (if saved to file)
        - error: Error message if any
    """
    # First get the download URLs
    url_data = await _fetch_download_urls(
        study_accession=study_accession,
        file_format=file_format,
        include_md5=True,
    )

    if "error" in url_data:
        return url_data

    if url_data["file_count"] == 0:
        return {
            "error": "No files found for this study",
            "study_accession": study_accession,
        }

    # Build the script
    script_lines = [
        "#!/bin/bash",
        f"# Download script for ENA study {study_accession}",
        "# Generated by RNA Dataset Search MCP",
        f"# Total files: {url_data['file_count']}",
        f"# Total size: {url_data['total_size_gb']} GB",
        "",
        "# Exit on error",
        "set -e",
        "",
    ]

    # Add download commands for each file
    for run in url_data["runs"]:
        script_lines.append(f"# Run: {run['run_accession']} ({run['size_gb']} GB)")
        for _i, url in enumerate(run["urls"]):
            if script_type == "wget":
                # wget -nc = no clobber (don't re-download existing files)
                script_lines.append(f"wget -nc {url}")
            elif script_type == "curl":
                # Extract filename from URL
                filename = url.split("/")[-1]
                # curl -C - = continue download if interrupted
                # -O = save with remote filename
                script_lines.append(f"curl -C - -O {url}")
            else:
                return {
                    "error": f"Unknown script type: {script_type}. Use 'wget' or 'curl'",
                    "study_accession": study_accession,
                }

        script_lines.append("")  # Empty line between runs

    # Add MD5 verification section
    if url_data["runs"] and "md5_checksums" in url_data["runs"][0]:
        script_lines.append("# MD5 Checksum verification")
        script_lines.append("echo 'Verifying MD5 checksums...'")
        script_lines.append("")

        for run in url_data["runs"]:
            for _i, (url, md5) in enumerate(zip(run["urls"], run.get("md5_checksums", []), strict=False)):
                filename = url.split("/")[-1]
                script_lines.append(f"echo '{md5}  {filename}' | md5sum -c -")

        script_lines.append("")
        script_lines.append("echo 'All files downloaded and verified successfully!'")

    script_content = "\n".join(script_lines)

    result = {
        "study_accession": study_accession,
        "script_content": script_content,
        "file_count": url_data["file_count"],
        "total_size_gb": url_data["total_size_gb"],
    }

    # Save to file if output_path provided
    if output_path:
        try:
            script_path = Path(output_path)
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(script_content)
            # Make script executable
            script_path.chmod(0o755)
            result["script_path"] = str(script_path)
            result["message"] = f"Download script saved to {script_path}"
        except (OSError, PermissionError) as e:
            result["error"] = f"Failed to save script: {e!s}"

    return result
