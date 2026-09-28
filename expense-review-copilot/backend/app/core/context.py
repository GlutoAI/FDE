"""Request-scoped identity passed to every tenant-owned read and write.

Authentication (phase 04) will build this from a verified session; until then the CLI and
tests construct it explicitly. Models and tool arguments never supply it.
"""

from pydantic import Field

from app.llm.contracts import Contract

TENANT_ID_PATTERN = r"^tenant_[a-z0-9_]+$"


class TenantScope(Contract):
    """The tenant on whose behalf a read or write runs."""

    tenant_id: str = Field(pattern=TENANT_ID_PATTERN, description="Owning tenant identifier")
