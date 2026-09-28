"""Expose configuration checks, data loading, indexing, search, MCP checks, and model probes.

Hosted model or embedding requests happen only when ``--live`` is passed to ``smoke``,
``index-documents``, or ``search``.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from time import monotonic
from typing import Literal

from pydantic import ValidationError

from app.agents.connection.models import ConnectionInput
from app.bootstrap import create_connection_agent
from app.core.context import TenantScope
from app.core.errors import AppError, ConfigurationError
from app.core.settings import (
    API_KEY_VARIABLES,
    DEFAULT_PROJECT_ROOT,
    ProjectLocation,
    Settings,
    load_embedding_profile,
    load_model_profile,
    load_settings,
)
from app.foundation import Foundation, import_seed_data, open_foundation
from app.llm.contracts import LiveProviderName
from app.mcp.client import load_mcp_catalog, open_role_toolsets
from app.rag.contracts import RetrievalQuery
from app.rag.ingestion import ingest_documents
from app.rag.retriever import Retriever

LIVE_COMMANDS = ("smoke", "index-documents", "search")
FOUNDATION_COMMANDS = ("data-import", "index-documents", "search", "mcp-check")
TENANT_COMMANDS = ("search", "mcp-check")
DIRECTORY_COMMANDS = ("data-import", "index-documents")
PREVIEW_CHARACTERS = 160


def run_cli() -> int:
    """Run the requested command and print only safe JSON metadata.

    Returns:
        Zero on success; one for any known configuration, data, storage, provider, or tool
        failure.
    """
    arguments = _parse_arguments()
    # SDK loggers can print request details; stdout carries only this command's JSON summary.
    for logger_name in ("openai", "anthropic", "httpx", "mcp", "fastmcp"):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    try:
        _validate_options(arguments)
        location = ProjectLocation(root=arguments.project_root.resolve())
        execution_mode = _select_execution_mode(arguments)
        settings = load_settings(location, execution_mode=execution_mode)
        if arguments.command == "config-check":
            return _print_configuration(location, settings)
        if arguments.command == "smoke":
            return asyncio.run(
                _run_smoke(location, settings, is_live=arguments.live, vendor=arguments.provider)
            )
        return asyncio.run(_run_foundation_command(arguments, location, settings))
    except AppError as error:
        print(json.dumps({"status": "failed", "reason": str(error)}))
        return 1


def _parse_arguments() -> argparse.Namespace:
    """Parse the command and its options from ``sys.argv``.

    Returns:
        The parsed arguments; which options belong to which command is checked later by
        ``_validate_options``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["config-check", "smoke", *FOUNDATION_COMMANDS])
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument(
        "--live", action="store_true", help="Authorize hosted requests for this command"
    )
    parser.add_argument(
        "--provider",
        choices=list(API_KEY_VARIABLES),
        help="Vendor for smoke --live; uses that vendor's profile from config/models.toml",
    )
    parser.add_argument("--tenant", help="Tenant for search and mcp-check, e.g. tenant_alpha")
    parser.add_argument("--query", help="Search text for the search command")
    parser.add_argument(
        "--directory",
        type=Path,
        help="data-import: data/raw/<source>/<date>; index-documents: data/raw/documents/<date>",
    )
    return parser.parse_args()


def _validate_options(arguments: argparse.Namespace) -> None:
    """Reject options that do not belong to the chosen command.

    Args:
        arguments: Parsed command-line arguments.

    Raises:
        ConfigurationError: An option is missing, misplaced, or malformed. The message names
            the option, never its value.
    """
    command = arguments.command
    if arguments.live and command not in LIVE_COMMANDS:
        raise ConfigurationError(f"invalid_option: --live belongs to {', '.join(LIVE_COMMANDS)}")
    if arguments.provider is not None and not (command == "smoke" and arguments.live):
        raise ConfigurationError("invalid_option: --provider belongs to smoke --live only")
    if command in TENANT_COMMANDS and not arguments.tenant:
        raise ConfigurationError(f"invalid_option: {command} requires --tenant")
    if command == "search" and not arguments.query:
        raise ConfigurationError("invalid_option: search requires --query")
    if (command in DIRECTORY_COMMANDS) != (arguments.directory is not None):
        raise ConfigurationError(
            f"invalid_option: --directory is required by {', '.join(DIRECTORY_COMMANDS)} only"
        )
    try:
        if arguments.tenant is not None:
            TenantScope(tenant_id=arguments.tenant)
        if arguments.query is not None:
            RetrievalQuery(text=arguments.query)
    except ValidationError as error:
        fields = ", ".join(sorted({str(issue["loc"][0]) for issue in error.errors()}))
        # "from None": a chained ValidationError carries the rejected input into any traceback.
        raise ConfigurationError(f"invalid_option: invalid {fields}") from None


def _select_execution_mode(arguments: argparse.Namespace) -> Literal["fixture", "live"] | None:
    """Return the mode for this invocation.

    Args:
        arguments: Parsed command-line arguments.

    Returns:
        None for ``config-check``, which reports the configured mode; otherwise ``live`` only
        when ``--live`` was passed, so configuration alone never enables hosted calls.
    """
    if arguments.command == "config-check":
        return None
    return "live" if arguments.live else "fixture"


def _print_configuration(location: ProjectLocation, settings: Settings) -> int:
    """Print nonsecret configuration, key presence per vendor, and the storage backend.

    Args:
        location: Project whose catalogs are validated.
        settings: Loaded settings; keys and the database URL are reported only as present.

    Returns:
        Zero; invalid catalogs raise before anything is printed.

    Raises:
        ConfigurationError: The model or MCP catalog is invalid.
    """
    profile = load_model_profile(location, settings)
    embedding = load_embedding_profile(location, settings)
    catalog = load_mcp_catalog(location)
    keys_present = {vendor: bool(settings.get_api_key(vendor)) for vendor in API_KEY_VARIABLES}
    database_url = settings.database_url.get_secret_value() if settings.database_url else None
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": settings.model_mode,
                "model": profile.model_id,
                "embedding_index": embedding.index_version,
                "database": "configured_url" if database_url else "sqlite:backend/data/app.db",
                "mcp_servers": sorted(catalog.servers),
                "tool_roles": sorted(catalog.roles),
                "keys_present": keys_present,
            }
        )
    )
    return 0


async def _run_smoke(
    location: ProjectLocation,
    settings: Settings,
    *,
    is_live: bool,
    vendor: LiveProviderName | None,
) -> int:
    """Run exactly one offline or explicitly authorized live probe, reporting elapsed time.

    Args:
        location: Project whose model catalog and prompt are used.
        settings: Loaded settings; their ``model_mode`` is overridden by ``is_live``.
        is_live: True only when ``--live`` was passed; sends one hosted request.
        vendor: Vendor from ``--provider``; None uses the configured profile.

    Returns:
        Zero after printing the validated output and its provenance.

    Raises:
        ConfigurationError: The profile, prompt, or selected vendor's key is invalid.
        ProviderError: The hosted request failed.
        AgentOutputError: The response broke the output contract.
    """
    mode = "live" if is_live else "fixture"
    # A config value alone must never turn the ordinary smoke command into a paid call.
    selected = settings.model_copy(update={"model_mode": mode})
    started = monotonic()
    async with create_connection_agent(location, selected, vendor=vendor) as agent:
        result = await agent.run_agent(ConnectionInput())
    print(
        json.dumps(
            {
                "mode": mode,
                "elapsed_seconds": round(monotonic() - started, 3),
                **result.model_dump(),
            }
        )
    )
    return 0


async def _run_foundation_command(
    arguments: argparse.Namespace, location: ProjectLocation, settings: Settings
) -> int:
    """Open the foundation once, run a data, retrieval, or MCP command, and print a summary.

    Args:
        arguments: Validated arguments naming one of ``FOUNDATION_COMMANDS``.
        location: Project whose configuration and database are used.
        settings: Loaded settings; ``model_mode`` selects fixture or hosted embeddings.

    Returns:
        Zero after printing the command's JSON summary.

    Raises:
        AppError: Any configuration, import, storage, embedding, or tool failure; ``run_cli``
            prints its safe message.
    """
    started = monotonic()
    async with open_foundation(location, settings) as foundation:
        payload = await _dispatch_foundation_command(arguments, location, foundation)
    elapsed = round(monotonic() - started, 3)
    summary = {"status": "ok", "mode": settings.model_mode, "elapsed_seconds": elapsed}
    print(json.dumps(summary | payload))
    return 0


async def _dispatch_foundation_command(
    arguments: argparse.Namespace, location: ProjectLocation, foundation: Foundation
) -> dict[str, object]:
    """Run the one foundation command named in ``arguments`` and return its JSON payload.

    Args:
        arguments: Validated arguments naming one of ``FOUNDATION_COMMANDS``.
        location: Project root passed to MCP servers.
        foundation: Open foundation the command runs against.

    Returns:
        Command-specific counts, results, or verified roles; never secrets or row values.

    Raises:
        AppError: The command failed; see the command's own function for the cases.
    """
    if arguments.command == "data-import":
        reports = await import_seed_data(foundation, arguments.directory.resolve())
        return {"imports": [report.model_dump() for report in reports]}
    if arguments.command == "index-documents":
        report = await ingest_documents(
            arguments.directory.resolve(), foundation.embedder, foundation.vector_store
        )
        return report.model_dump()
    if arguments.command == "search":
        return await _search_documents(foundation.retriever, arguments)
    return await _check_mcp_roles(location, foundation, arguments.tenant)


async def _search_documents(
    retriever: Retriever, arguments: argparse.Namespace
) -> dict[str, object]:
    """Return the tenant's best passages with document IDs, scores, and short previews.

    Args:
        retriever: Search over the active embedding profile's index.
        arguments: Validated arguments carrying ``--tenant`` and ``--query``.

    Returns:
        ``{"results": [...]}``, best first; previews are cut to ``PREVIEW_CHARACTERS``.

    Raises:
        EmbeddingError: The query could not be embedded.
        StorageError: The search failed.
    """
    scope = TenantScope(tenant_id=arguments.tenant)
    results = await retriever.search_chunks(scope, RetrievalQuery(text=arguments.query))
    return {
        "results": [
            {
                "document_id": result.chunk.document_id,
                "chunk_id": result.chunk.chunk_id,
                "score": round(result.score, 4),
                "preview": result.chunk.text[:PREVIEW_CHARACTERS],
            }
            for result in results
        ]
    }


async def _check_mcp_roles(
    location: ProjectLocation, foundation: Foundation, tenant_id: str
) -> dict[str, object]:
    """Start each role's servers, verify their catalogs, and report the roles checked.

    Args:
        location: Project root passed to each server process.
        foundation: Open foundation providing the MCP catalog and database URL.
        tenant_id: Tenant each server process is launched for.

    Returns:
        The verified role names and every catalog server name, sorted.

    Raises:
        ToolAccessError: A server failed to start or advertised an unexpected catalog.
    """
    scope = TenantScope(tenant_id=tenant_id)
    checked = []
    for role in sorted(foundation.mcp_catalog.roles):
        async with open_role_toolsets(
            location,
            foundation.mcp_catalog,
            role=role,
            scope=scope,
            database_url=foundation.database_url,
        ):
            checked.append(role)
    return {"verified_roles": checked, "servers": sorted(foundation.mcp_catalog.servers)}


if __name__ == "__main__":
    raise SystemExit(run_cli())
