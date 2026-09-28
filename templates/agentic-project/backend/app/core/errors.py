"""The application's exception hierarchy; every message is safe to print or return.

Messages start with a stable machine-readable code (``storage_failed: ...``) and never contain
credentials, provider response bodies, or row values. The CLI and HTTP routes catch ``AppError``
and show ``str(error)``; anything else is a bug and propagates.
"""


class AppError(Exception):
    """A known application failure with a safe, credential-free public message."""


class ConfigurationError(AppError):
    """Configuration is absent, malformed, or unsupported by this foundation."""


class ProviderError(AppError):
    """A model request failed; its message contains only a normalized error code."""


class AgentOutputError(AppError):
    """An agent received a model response that is incomplete or breaks its output contract."""


class AgentInputError(AppError):
    """The caller supplied input that violates the agent request schema."""


class StorageError(AppError):
    """A database operation failed; the message names the failure class, never row values."""


class RecordNotFoundError(AppError, LookupError):
    """No record with the requested key exists for the requesting tenant.

    Records owned by another tenant are reported the same way, so callers cannot probe them.
    """


class InvalidQueryError(AppError, ValueError):
    """A caller asked for an unbounded or malformed read."""


class DataImportError(AppError):
    """A source file failed validation; nothing from that import was written."""


class EmbeddingError(AppError):
    """An embedding request failed or returned vectors of the wrong shape."""


class AccessDeniedError(AppError, PermissionError):
    """The requesting tenant does not own the resource it tried to read or change."""


class ToolAccessError(AppError):
    """A tool call was denied, unknown, or returned output outside its declared contract."""
