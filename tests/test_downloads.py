"""Tests for data download functionality.

Tests focus on:
- Getting download URLs for studies
- Generating download scripts (wget/curl)
- File format options
- Edge cases and error handling
"""

import pytest


@pytest.mark.asyncio
async def test_get_download_urls_basic(mcp_client, sample_study_accession):
    """Test getting FASTQ download URLs for a study."""
    result = await mcp_client.call_tool(
        "get_download_urls",
        {
            "study_accession": sample_study_accession,
            "file_format": "fastq",
        },
    )

    data = result.data
    assert data["study_accession"] == sample_study_accession
    assert data["file_count"] > 0, "Study should have files"
    assert data["total_size_gb"] > 0, "Should calculate total size"
    assert isinstance(data["runs"], list)
    assert len(data["runs"]) > 0, "Should have runs"


@pytest.mark.asyncio
async def test_download_urls_include_md5(mcp_client, sample_study_accession):
    """Test that MD5 checksums are included by default."""
    result = await mcp_client.call_tool(
        "get_download_urls",
        {
            "study_accession": sample_study_accession,
            "include_md5": True,
        },
    )

    data = result.data
    if data["runs"]:
        first_run = data["runs"][0]
        assert "md5_checksums" in first_run, "Should include MD5 checksums"
        assert len(first_run["md5_checksums"]) == len(first_run["urls"]), "Should have MD5 for each file"


@pytest.mark.asyncio
async def test_download_urls_proper_formatting(mcp_client, sample_study_accession):
    """Test that URLs are properly formatted with ftp:// prefix."""
    result = await mcp_client.call_tool(
        "get_download_urls",
        {"study_accession": sample_study_accession},
    )

    data = result.data
    if data["runs"]:
        first_run = data["runs"][0]
        assert "run_accession" in first_run
        assert "urls" in first_run
        assert len(first_run["urls"]) > 0

        # All URLs should start with ftp://
        for url in first_run["urls"]:
            assert url.startswith("ftp://"), f"URL should start with ftp://: {url}"
            assert ".fastq.gz" in url, "FASTQ URLs should point to .fastq.gz files"


@pytest.mark.asyncio
async def test_download_urls_paired_end_reads(mcp_client, sample_study_accession):
    """Test handling of paired-end reads (multiple files per run)."""
    result = await mcp_client.call_tool(
        "get_download_urls",
        {"study_accession": sample_study_accession},
    )

    data = result.data
    # Some runs should have paired-end data (2 files)
    if data["runs"]:
        file_counts = [run["file_count"] for run in data["runs"]]
        # Most RNA-seq is paired-end
        assert any(count >= 2 for count in file_counts), "Should find paired-end runs"


@pytest.mark.asyncio
async def test_generate_wget_script(mcp_client, sample_study_accession):
    """Test generating a wget download script."""
    result = await mcp_client.call_tool(
        "generate_download_script",
        {
            "study_accession": sample_study_accession,
            "script_type": "wget",
        },
    )

    data = result.data
    assert data["study_accession"] == sample_study_accession
    assert "script_content" in data
    assert data["file_count"] > 0
    assert data["total_size_gb"] > 0

    script = data["script_content"]
    # Verify script structure
    assert "#!/bin/bash" in script, "Should be a bash script"
    assert "set -e" in script, "Should exit on error"
    assert "wget -nc" in script, "Should use wget with no-clobber option"
    assert "ftp://" in script, "Should include FTP URLs"
    assert sample_study_accession in script, "Should reference study accession"


@pytest.mark.asyncio
async def test_generate_wget_script_with_md5(mcp_client, sample_study_accession):
    """Test that wget script includes MD5 verification commands."""
    result = await mcp_client.call_tool(
        "generate_download_script",
        {
            "study_accession": sample_study_accession,
            "script_type": "wget",
        },
    )

    script = result.data["script_content"]
    assert "md5sum" in script, "Should include MD5 verification"
    assert "md5sum -c" in script, "Should check MD5 checksums"


@pytest.mark.asyncio
async def test_generate_curl_script(mcp_client, sample_study_accession):
    """Test generating a curl download script as alternative to wget."""
    result = await mcp_client.call_tool(
        "generate_download_script",
        {
            "study_accession": sample_study_accession,
            "script_type": "curl",
        },
    )

    data = result.data
    script = data["script_content"]

    assert "#!/bin/bash" in script
    assert "curl -C - -O" in script, "Should use curl with resume and save options"
    assert "ftp://" in script
    assert "wget" not in script, "Should not mix curl and wget"


@pytest.mark.asyncio
async def test_download_script_file_count_matches(mcp_client, sample_study_accession):
    """Test that script file count matches actual number of files."""
    # Get URLs
    urls_result = await mcp_client.call_tool(
        "get_download_urls",
        {"study_accession": sample_study_accession},
    )

    # Generate script
    script_result = await mcp_client.call_tool(
        "generate_download_script",
        {"study_accession": sample_study_accession},
    )

    # File counts should match
    assert urls_result.data["file_count"] == script_result.data["file_count"]


@pytest.mark.asyncio
async def test_download_script_without_saving(mcp_client, sample_study_accession):
    """Test generating script without saving to file (return content only)."""
    result = await mcp_client.call_tool(
        "generate_download_script",
        {
            "study_accession": sample_study_accession,
            # No output_path provided
        },
    )

    data = result.data
    assert "script_content" in data
    assert "script_path" not in data, "Should not save when no output_path provided"
    assert "error" not in data


@pytest.mark.asyncio
async def test_download_different_file_formats(mcp_client, sample_study_accession):
    """Test requesting different file formats (fastq, sra)."""
    # Test FASTQ format
    fastq_result = await mcp_client.call_tool(
        "get_download_urls",
        {
            "study_accession": sample_study_accession,
            "file_format": "fastq",
        },
    )

    assert fastq_result.data["file_count"] > 0

    # Test SRA format (might not always be available)
    sra_result = await mcp_client.call_tool(
        "get_download_urls",
        {
            "study_accession": sample_study_accession,
            "file_format": "sra",
        },
    )

    # SRA format should at least not error
    assert "study_accession" in sra_result.data
