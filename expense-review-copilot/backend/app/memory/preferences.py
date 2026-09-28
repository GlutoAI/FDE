"""Approved long-term preferences: their contract, import, and the active-preference filter."""

import json
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import AwareDatetime, Field, TypeAdapter, ValidationError

from app.core.clock import Clock
from app.core.context import TenantScope
from app.core.errors import DataImportError
from app.db.records import RECORD_KEY_PATTERN, TenantRecord
from app.db.repository import MAX_LIST_LIMIT, RecordRepository


class MemoryPreference(TenantRecord):
    """A user-approved stylistic or reporting preference, valid until it expires."""

    key_field: ClassVar[str] = "preference_id"

    preference_id: str = Field(pattern=RECORD_KEY_PATTERN, description="Preference identifier")
    expense_id: str | None = Field(description="Expense it applies to; None for tenant-wide")
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="Preference name")
    value: str = Field(min_length=1, max_length=500, description="Preference text; untrusted")
    approved_by: str = Field(pattern=RECORD_KEY_PATTERN, description="User who approved it")
    status: Literal["approved", "pending", "revoked"] = Field(description="Approval state")
    source: str = Field(min_length=1, description="How the preference was captured")
    created_at: AwareDatetime = Field(description="When it was recorded")
    expires_at: AwareDatetime | None = Field(description="When it stops applying; None never")

    def is_active_at(self, now: AwareDatetime) -> bool:
        """Return whether the preference is approved, started, and unexpired at ``now``.

        Args:
            now: The instant to check.

        Returns:
            True only for approved preferences with ``created_at <= now < expires_at``.
        """
        has_expired = self.expires_at is not None and self.expires_at <= now
        return self.status == "approved" and self.created_at <= now and not has_expired


PREFERENCES_ADAPTER = TypeAdapter(list[MemoryPreference])


class PreferenceMemory:
    """Reads the preferences an agent may use now, for one tenant and optionally one expense."""

    def __init__(self, repository: RecordRepository[MemoryPreference], clock: Clock) -> None:
        """Compose storage and the time source used for expiry.

        Args:
            repository: Tenant-scoped preference storage.
            clock: Source of the current time.
        """
        self._repository = repository
        self._clock = clock

    async def list_active_preferences(
        self, scope: TenantScope, *, expense_id: str | None = None
    ) -> list[MemoryPreference]:
        """Return tenant-wide preferences plus those for ``expense_id``, if active now.

        Args:
            scope: Tenant the caller acts for.
            expense_id: Expense being reviewed; None returns tenant-wide ones only.

        Returns:
            Active preferences ordered by ID; pending, revoked, and expired ones are excluded.
            Only the tenant's first ``MAX_LIST_LIMIT`` stored preferences are considered.

        Raises:
            StorageError: The read failed.
        """
        now = self._clock.get_current_time()
        stored = await self._repository.list_records(scope, limit=MAX_LIST_LIMIT)
        return [
            preference
            for preference in stored
            if preference.expense_id in (None, expense_id) and preference.is_active_at(now)
        ]


def load_preference_records(path: Path) -> list[MemoryPreference]:
    """Read and validate a preferences JSON file.

    Args:
        path: JSON array of preference objects.

    Returns:
        Validated preferences in file order.

    Raises:
        DataImportError: The file is unreadable or any entry is invalid.
    """
    try:
        return PREFERENCES_ADAPTER.validate_python(
            json.loads(path.read_text(encoding="utf-8")), strict=False
        )
    except (OSError, ValueError, ValidationError) as error:
        raise DataImportError(f"invalid_preferences: {path.name}") from error
