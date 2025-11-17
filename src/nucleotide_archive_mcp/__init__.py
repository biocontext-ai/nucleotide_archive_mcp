from importlib.metadata import version

from nucleotide_archive_mcp.main import run_app
from nucleotide_archive_mcp.mcp import mcp

__version__ = version("nucleotide_archive_mcp")

__all__ = ["mcp", "run_app", "__version__"]


if __name__ == "__main__":
    run_app()
