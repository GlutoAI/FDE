"""Safe diagnostic errors; provider response bodies must never reach the CLI."""


class ExpenseError(Exception):
    """A known application failure with a safe, credential-free public message."""


class ConfigurationError(ExpenseError):
    """Configuration is absent, malformed, or unsupported by this foundation."""


class ProviderError(ExpenseError):
    """A model request failed; its message contains only a normalized error code."""


class AgentOutputError(ExpenseError):
    """The connection agent received an unexpected or incomplete model response."""


class AgentInputError(ExpenseError):
    """The caller supplied input that violates the agent request schema."""


class StorageError(ExpenseError):
    """A database operation failed; the message names the failure class, never row values."""


class RecordNotFoundError(ExpenseError, LookupError):
    """No record with the requested key exists for the requesting tenant.

    Records owned by another tenant are reported the same way, so callers cannot probe them.
    """


class InvalidQueryError(ExpenseError, ValueError):
    """A caller asked for an unbounded or malformed read."""


class DataImportError(ExpenseError):
    """A source file failed validation; nothing from that import was written."""


class EmbeddingError(ExpenseError):
    """An embedding request failed or returned vectors of the wrong shape."""


class AccessDeniedError(ExpenseError, PermissionError):
    """The requesting tenant does not own the resource it tried to read or change."""


class ToolAccessError(ExpenseError):
    """A tool call was denied, unknown, or returned output outside its declared contract."""
