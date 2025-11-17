"""Tools for downloading RNA-seq data from ENA."""

from pathlib import Path
from typing import Annotated

import httpx

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
    study_accession: Annotated[str, "Study accession from search_rna_studies (e.g., 'PRJDB2345')"],
    file_format: Annotated[str, "File format: 'fastq', 'submitted', or 'sra'"] = "fastq",
    include_md5: Annotated[bool, "Include MD5 checksums for file verification"] = True,
) -> dict:
    """Get FTP download URLs for all sequencing data files in a study.

    **LLM Usage**: Call after search_rna_studies() to get download URLs for selected studies.
    Returns FTP URLs that can be used with wget/curl or passed to generate_download_script().

    Parameters
    ----------
    study_accession : str
        Study accession from search results (e.g., "PRJDB2345", "PRJNA123456", "SRP417965")
    file_format : str, optional
        File format: "fastq" (processed FASTQ files, most common), "submitted" (original
        submitted files), "sra" (SRA format). Default: "fastq"
    include_md5 : bool, optional
        Include MD5 checksums for file integrity verification. Default: True

    Returns
    -------
    dict
        - study_accession (str): Queried study
        - file_count (int): Total number of files
        - total_size_gb (float): Total download size in GB
        - runs (list[dict]): Per-run file info, each containing:
            - run_accession: Run identifier
            - file_count: Files in this run (2 for paired-end)
            - size_gb: Run size in GB
            - urls: List of FTP URLs (ftp://...)
            - md5_checksums: List of MD5 hashes (if include_md5=True)

    Examples
    --------
    Get FASTQ URLs after finding studies:
        study_accession="PRJDB2345"

    Check file sizes before downloading:
        study_accession="SRP417965", file_format="fastq"
    """
    return await _fetch_download_urls(study_accession, file_format, include_md5)


@mcp.tool
async def generate_download_script(
    study_accession: Annotated[str, "Study accession from search_rna_studies"],
    output_path: Annotated[str | None, "Save path for script (e.g., './download.sh'). None=return only"] = None,
    script_type: Annotated[str, "Download tool: 'wget' or 'curl'"] = "wget",
    file_format: Annotated[str, "File format: 'fastq', 'submitted', or 'sra'"] = "fastq",
) -> dict:
    """Generate executable bash script to download all study data files.

    **LLM Usage**: After identifying interesting studies, generate a download script for the
    user to execute. Returns script content and optionally saves to file. Script includes
    MD5 verification commands.

    **Typical workflow**:
    1. search_rna_studies() → find studies
    2. get_study_details() → verify it's the right study
    3. generate_download_script() → create download script
    4. User executes the script to download data

    Parameters
    ----------
    study_accession : str
        Study accession (e.g., "PRJDB2345", "SRP417965")
    output_path : str, optional
        File path to save script (e.g., "./download_study.sh"). If None, returns
        script content without saving. Script will be made executable (chmod 755).
    script_type : str, optional
        Download tool: "wget" (recommended, resumable with -nc) or "curl" (resumable with -C -)
    file_format : str, optional
        File format: "fastq" (most common), "submitted", "sra"

    Returns
    -------
    dict
        - study_accession (str): Queried study
        - script_content (str): Complete bash script (can be directly executed)
        - file_count (int): Number of files script will download
        - total_size_gb (float): Total download size
        - script_path (str): Save location (if output_path provided)
        - message (str): Success/error message

    Examples
    --------
    Generate and return wget script:
        study_accession="PRJDB2345"

    Save wget script to file (recommended):
        study_accession="SRP417965", output_path="./download_srp417965.sh"

    Generate curl-based script:
        study_accession="PRJDB2345", script_type="curl"
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
