"""Configuration for RNA Dataset Search MCP server."""

import os
from enum import Enum
from typing import Final

# ENA API Configuration
ENA_PORTAL_API_BASE: Final[str] = os.getenv("ENA_PORTAL_API_BASE", "https://www.ebi.ac.uk/ena/portal/api")
ENA_BROWSER_API_BASE: Final[str] = os.getenv("ENA_BROWSER_API_BASE", "https://www.ebi.ac.uk/ena/browser/api")
DEFAULT_TIMEOUT: Final[float] = float(os.getenv("ENA_TIMEOUT", "30.0"))
DEFAULT_SEARCH_LIMIT: Final[int] = int(os.getenv("ENA_SEARCH_LIMIT", "20"))

# Logging Configuration
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")

# Rate Limiting (requests per second)
MAX_REQUESTS_PER_SECOND: Final[float] = float(os.getenv("ENA_MAX_RPS", "10.0"))


# ==============================================================================
# ENA Controlled Vocabularies - Enums for Type Safety
# ==============================================================================


class LibraryStrategy(str, Enum):
    """ENA library strategy controlled vocabulary.

    Source: https://ena-docs.readthedocs.io/en/latest/submit/reads/webin-cli.html
    """

    # Whole Genome Sequencing
    WGS = "WGS"  # Whole Genome Sequencing
    WGA = "WGA"  # Whole Genome Amplification
    WXS = "WXS"  # Whole Exome Sequencing
    WCS = "WCS"  # Whole Chromosome Sequencing

    # RNA Sequencing
    RNA_SEQ = "RNA-Seq"  # Whole Transcriptome Shotgun Sequencing
    SNRNA_SEQ = "snRNA-seq"  # Single nucleus RNA sequencing
    SSRNA_SEQ = "ssRNA-seq"  # Strand-specific RNA sequencing
    MIRNA_SEQ = "miRNA-Seq"  # Micro RNA sequencing
    NCRNA_SEQ = "ncRNA-Seq"  # Non-coding RNA sequencing
    FL_CDNA = "FL-cDNA"  # Full-length cDNA sequencing
    EST = "EST"  # Expressed Sequence Tag

    # Functional Genomics - RNA
    RIBO_SEQ = "Ribo-Seq"  # Ribosome profiling
    RIP_SEQ = "RIP-Seq"  # RNA immunoprecipitation sequencing

    # Chromatin Structure
    HI_C = "Hi-C"  # Chromosome Conformation Capture
    ATAC_SEQ = "ATAC-seq"  # Assay for Transposase-Accessible Chromatin
    CHIP_SEQ = "ChIP-Seq"  # Chromatin Immunoprecipitation sequencing
    MNASE_SEQ = "MNase-Seq"  # Micrococcal Nuclease sequencing
    DNASE_HYPERSENSITIVITY = "DNase-Hypersensitivity"  # DNase-seq
    FAIRE_SEQ = "FAIRE-seq"  # Formaldehyde Assisted Isolation of Regulatory Elements
    CHIA_PET = "ChIA-PET"  # Chromatin Interaction Analysis by Paired-End Tag
    TETHERED_CHROMATIN_CONFORMATION_CAPTURE = "Tethered Chromatin Conformation Capture"

    # DNA Methylation
    BISULFITE_SEQ = "Bisulfite-Seq"  # Bisulfite sequencing (MethylC-seq)
    MRE_SEQ = "MRE-Seq"  # Methylation-Sensitive Restriction Enzyme Sequencing
    MEDIP_SEQ = "MeDIP-Seq"  # Methylated DNA Immunoprecipitation Sequencing
    MBD_SEQ = "MBD-Seq"  # Methyl CpG Binding Domain Sequencing
    NOME_SEQ = "NOMe-Seq"  # Nucleosome Occupancy and Methylome sequencing
    CHM_SEQ = "ChM-Seq"  # ChIPmentation

    # Targeted/Amplicon
    AMPLICON = "AMPLICON"  # PCR or RT-PCR products
    TARGETED_CAPTURE = "Targeted-Capture"  # Enrichment of targeted loci
    RAD_SEQ = "RAD-Seq"  # Restriction site associated DNA

    # Clone-based
    CLONE = "CLONE"  # Clone-based hierarchical sequencing
    POOLCLONE = "POOLCLONE"  # Shotgun of pooled clones
    CLONEEND = "CLONEEND"  # Clone end sequencing
    FINISHING = "FINISHING"  # Gap closing sequencing

    # Other Methods
    TN_SEQ = "Tn-Seq"  # Transposon sequencing for fitness determination
    GBS = "GBS"  # Genotyping by sequencing
    CTS = "CTS"  # Concatenated Tag Sequencing
    SELEX = "SELEX"  # Systematic Evolution of Ligands
    SYNTHETIC_LONG_READ = "Synthetic-Long-Read"  # Binning and barcoding
    VALIDATION = "VALIDATION"  # Re-evaluation of variants
    OTHER = "OTHER"  # Library strategy not listed


class LibrarySource(str, Enum):
    """ENA library source controlled vocabulary.

    Source: https://ena-docs.readthedocs.io/en/latest/submit/reads/webin-cli.html
    """

    TRANSCRIPTOMIC = "TRANSCRIPTOMIC"  # Bulk transcriptomic material
    TRANSCRIPTOMIC_SINGLE_CELL = "TRANSCRIPTOMIC SINGLE CELL"  # Single-cell transcriptomic
    GENOMIC = "GENOMIC"  # Genomic DNA
    GENOMIC_SINGLE_CELL = "GENOMIC SINGLE CELL"  # Single-cell genomic DNA
    METAGENOMIC = "METAGENOMIC"  # Metagenomic material
    METATRANSCRIPTOMIC = "METATRANSCRIPTOMIC"  # Metatranscriptomic material
    SYNTHETIC = "SYNTHETIC"  # Synthetic DNA
    VIRAL_RNA = "VIRAL RNA"  # Viral RNA
    OTHER = "OTHER"  # Other source material


# ==============================================================================
# Legacy string dictionaries (kept for backward compatibility)
# ==============================================================================

# ENA Controlled Vocabularies - Library Strategy
# Source: https://ena-docs.readthedocs.io/en/latest/submit/reads/webin-cli.html
LIBRARY_STRATEGIES: Final[dict[str, str]] = {
    strategy.value: strategy.name.replace("_", "-") for strategy in LibraryStrategy
}

# ENA Controlled Vocabularies - Library Source
LIBRARY_SOURCES: Final[dict[str, str]] = {source.value: source.name.replace("_", " ") for source in LibrarySource}

# Predefined technology filter presets for common use cases
TECHNOLOGY_PRESETS: Final[dict[str, dict[str, str | list[str]]]] = {
    "bulk": {
        "description": "Standard bulk RNA-seq",
        "strategies": ["RNA-Seq"],
        "sources": ["TRANSCRIPTOMIC"],
    },
    "single-cell": {
        "description": "Single-cell/nucleus RNA-seq",
        "strategies": ["RNA-Seq", "snRNA-seq", "ssRNA-seq"],
        "sources": ["TRANSCRIPTOMIC SINGLE CELL"],
    },
    "small-rna": {
        "description": "Small RNA sequencing (miRNA, ncRNA)",
        "strategies": ["miRNA-Seq", "ncRNA-Seq"],
        "sources": ["TRANSCRIPTOMIC"],
    },
    "ribo-seq": {
        "description": "Ribosome profiling",
        "strategies": ["Ribo-Seq"],
        "sources": ["TRANSCRIPTOMIC"],
    },
    "rna-all": {
        "description": "All RNA sequencing types",
        "strategies": [
            "RNA-Seq",
            "snRNA-seq",
            "ssRNA-seq",
            "miRNA-Seq",
            "ncRNA-Seq",
            "FL-cDNA",
            "EST",
            "Ribo-Seq",
            "RIP-Seq",
        ],
        "sources": ["TRANSCRIPTOMIC", "TRANSCRIPTOMIC SINGLE CELL"],
    },
}

# Default organism for searches
DEFAULT_ORGANISM: Final[str] = "Homo sapiens"

# Common organism mappings
COMMON_ORGANISMS: Final[dict[str, str]] = {
    "human": "Homo sapiens",
    "mouse": "Mus musculus",
    "rat": "Rattus norvegicus",
    "zebrafish": "Danio rerio",
    "fly": "Drosophila melanogaster",
    "worm": "Caenorhabditis elegans",
    "yeast": "Saccharomyces cerevisiae",
}
