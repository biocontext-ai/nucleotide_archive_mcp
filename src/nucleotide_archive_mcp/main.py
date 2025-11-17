import enum
import logging
import sys
from typing import Literal

import click

from nucleotide_archive_mcp.config import LOG_LEVEL

from .tools import *  # noqa: F403 import all tools to register them

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


TransportType = Literal["stdio", "http", "sse", "streamable-http"]


class EnvironmentType(enum.Enum):
    """Enum to define environment type."""

    PRODUCTION = enum.auto()
    DEVELOPMENT = enum.auto()


@click.command(name="run")
@click.option(
    "-t",
    "--transport",
    "transport",
    type=str,
    help="MCP transport option. Defaults to 'stdio'.",
    default="stdio",
    envvar="MCP_TRANSPORT",
)
@click.option(
    "-p",
    "--port",
    "port",
    type=int,
    help="Port of MCP server. Defaults to '8000'",
    default=8000,
    envvar="MCP_PORT",
    required=False,
)
@click.option(
    "-h",
    "--host",
    "hostname",
    type=str,
    help="Hostname of MCP server. Defaults to '0.0.0.0'",
    default="0.0.0.0",
    envvar="MCP_HOSTNAME",
    required=False,
)
@click.option("-v", "--version", "version", is_flag=True, help="Get version of package.")
@click.option(
    "-e",
    "--env",
    "environment",
    type=click.Choice(EnvironmentType, case_sensitive=False),
    default=EnvironmentType.DEVELOPMENT,
    envvar="MCP_ENVIRONMENT",
    help="MCP server environment. Defaults to 'development'.",
)
def run_app(
    transport: str = "stdio",
    port: int = 8000,
    hostname: str = "0.0.0.0",
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT,
    version: bool = False,
):
    """Run the MCP server "nucleotide_archive_mcp".

    Use the EMBL-EBI ENA search API to find suitable bulk and scRNAseq datasets for your research or product development.
    If the environment variable MCP_ENVIRONMENT is set to "PRODUCTION", it will run the Starlette app with streamable HTTP for the MCP server. Otherwise, it will run the MCP server via stdio.
    The port is set via "-p/--port" or the MCP_PORT environment variable, defaulting to "8000" if not set.
    The hostname is set via "-h/--host" or the MCP_HOSTNAME environment variable, defaulting to "0.0.0.0" if not set.
    To specify to transform method of the MCP server, set "-e/--env" or the MCP_TRANSPORT environment variable, which defaults to "stdio".
    """
    if version is True:
        from nucleotide_archive_mcp import __version__

        click.echo(__version__)
        sys.exit(0)

    logger = logging.getLogger(__name__)

    from nucleotide_archive_mcp.mcp import mcp

    # Validate transport type
    valid_transports: tuple[TransportType, ...] = ("stdio", "http", "sse", "streamable-http")
    if transport not in valid_transports:
        logger.error(f"Invalid transport: {transport}. Must be one of: {valid_transports}")
        sys.exit(1)

    transport_typed: TransportType = transport  # type: ignore[assignment]

    if environment == EnvironmentType.DEVELOPMENT:
        logger.info("Starting MCP server (DEVELOPMENT mode)")
        if transport == "http":
            mcp.run(transport=transport_typed, port=port, host=hostname)
        else:
            mcp.run(transport=transport_typed)
    else:
        raise NotImplementedError()
        # logger.info("Starting Starlette app with Uvicorn in PRODUCTION mode.")
        # uvicorn.run(app, host=hostname, port=port)


if __name__ == "__main__":
    run_app()
