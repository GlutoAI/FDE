"""Safe diagnostic errors; provider response bodies must never reach the CLI."""


class CashflowError(Exception):
    """A known application failure with a safe, credential-free public message."""


class ConfigurationError(CashflowError):
    """Configuration is absent, malformed, or unsupported by this foundation."""


class ProviderError(CashflowError):
    """A model request failed; its message contains only a normalized error code."""


class AgentOutputError(CashflowError):
    """The connection agent received an unexpected or incomplete model response."""


class AgentInputError(CashflowError):
    """The caller supplied input that violates the agent request schema."""


class StorageError(CashflowError):
    """A database operation failed; the message names the failure class, never row values."""


class RecordNotFoundError(CashflowError, LookupError):
    """No record with the requested key exists for the requesting tenant.

    Records owned by another tenant are reported the same way, so callers cannot probe them.
    """


class InvalidQueryError(CashflowError, ValueError):
    """A caller asked for an unbounded or malformed read."""


class DataImportError(CashflowError):
    """A source file failed validation; nothing from that import was written."""


class EmbeddingError(CashflowError):
    """An embedding request failed or returned vectors of the wrong shape."""


class AccessDeniedError(CashflowError, PermissionError):
    """The requesting tenant does not own the resource it tried to read or change."""


class ToolAccessError(CashflowError):
    """A tool call was denied, unknown, or returned output outside its declared contract."""
