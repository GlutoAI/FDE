"""Sources of the current time; code that needs "now" receives a Clock instead of reading it."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import override


class Clock(ABC):
    """A source of the current time, substitutable so tests can freeze it."""

    @abstractmethod
    def get_current_time(self) -> datetime:
        """Return the current time.

        Returns:
            A timezone-aware datetime in UTC.
        """


class SystemClock(Clock):
    """A clock that reads the operating system time."""

    @override
    def get_current_time(self) -> datetime:
        return datetime.now(tz=UTC)


class FrozenClock(Clock):
    """A clock fixed at one instant, for deterministic tests.

    Attributes:
        frozen_at: The instant every call returns.
    """

    def __init__(self, frozen_at: datetime) -> None:
        """Fix the clock.

        Args:
            frozen_at: A timezone-aware instant.

        Raises:
            ValueError: ``frozen_at`` is naive.
        """
        if frozen_at.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self.frozen_at = frozen_at.astimezone(UTC)

    @override
    def get_current_time(self) -> datetime:
        return self.frozen_at
