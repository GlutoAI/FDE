"""Verify conversation history and preference memory; one suite runs on both stores."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.clock import FrozenClock, SystemClock
from app.core.errors import AccessDeniedError, DataImportError, InvalidQueryError, StorageError
from app.db.csv_import import import_structured_data
from app.db.repository import InMemoryRecordRepository, SqlRecordRepository
from app.db.tables import memory_preferences
from app.memory.conversation import (
    ConversationStore,
    InMemoryConversationStore,
    SqlConversationStore,
)
from app.memory.preferences import (
    MemoryPreference,
    PreferenceMemory,
    load_preference_records,
)
from tests.synthetic import ALPHA, BETA, run_with_engine, write_record_import

BEFORE_EXPIRY = FrozenClock(datetime(2026, 9, 27, tzinfo=UTC))


def build_exchange(number: int) -> list[ModelMessage]:
    """Return one numbered user question and model answer, as Pydantic AI stores them."""
    return [
        ModelRequest(parts=[UserPromptPart(content=f"question {number}")]),
        ModelResponse(parts=[TextPart(content=f"answer {number}")]),
    ]


def read_texts(messages: list[ModelMessage]) -> list[str]:
    """Return the text of every message part, in order, for readable assertions."""
    return [str(part.content) for message in messages for part in message.parts]  # type: ignore[union-attr]


StoreFactory = Callable[[AsyncEngine], ConversationStore]
STORE_FACTORIES: dict[str, StoreFactory] = {
    "memory": lambda engine: InMemoryConversationStore(),
    "sql": SqlConversationStore,
}


@pytest.fixture(params=sorted(STORE_FACTORIES))
def store_factory(request: pytest.FixtureRequest) -> StoreFactory:
    return STORE_FACTORIES[request.param]


def test_frozen_clock_normalizes_to_utc_and_rejects_naive_time() -> None:
    eastern = datetime(2026, 9, 27, 8, tzinfo=timezone(timedelta(hours=-4)))
    assert FrozenClock(eastern).get_current_time() == datetime(2026, 9, 27, 12, tzinfo=UTC)
    assert SystemClock().get_current_time().tzinfo == UTC
    with pytest.raises(ValueError):
        FrozenClock(datetime(2026, 9, 27))


def test_conversation_store_appends_and_returns_recent_window_in_order(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        store = store_factory(engine)
        assert await store.save_messages(ALPHA, "thread-1", build_exchange(1)) == 2
        await store.save_messages(ALPHA, "thread-1", build_exchange(2))
        everything = await store.load_messages(ALPHA, "thread-1", limit=10)
        assert read_texts(everything) == ["question 1", "answer 1", "question 2", "answer 2"]
        window = await store.load_messages(ALPHA, "thread-1", limit=2)
        assert read_texts(window) == ["question 2", "answer 2"]
        assert await store.load_messages(ALPHA, "unknown-thread", limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_conversation_store_denies_other_tenant_reads_and_writes(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        store = store_factory(engine)
        await store.save_messages(ALPHA, "thread-1", build_exchange(1))
        with pytest.raises(AccessDeniedError):
            await store.load_messages(BETA, "thread-1", limit=10)
        with pytest.raises(AccessDeniedError):
            await store.save_messages(BETA, "thread-1", build_exchange(2))
        assert len(await store.load_messages(ALPHA, "thread-1", limit=10)) == 2

    run_with_engine(tmp_path, scenario)


@pytest.mark.parametrize("limit", [0, 201])
def test_conversation_store_rejects_unbounded_history(
    tmp_path: Path, store_factory: StoreFactory, limit: int
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(InvalidQueryError):
            await store_factory(engine).load_messages(ALPHA, "thread-1", limit=limit)

    run_with_engine(tmp_path, scenario)


def test_sql_conversation_history_feeds_a_later_agent_run(tmp_path: Path) -> None:
    agent = Agent(TestModel(custom_output_text="noted"), instructions="Remember the thread.")

    async def scenario(engine: AsyncEngine) -> None:
        store = SqlConversationStore(engine)
        first = await agent.run("My preferred report day is Monday.")
        await store.save_messages(ALPHA, "thread-1", first.new_messages())
        history = await store.load_messages(ALPHA, "thread-1", limit=50)
        second = await agent.run("What did I say?", message_history=history)
        assert "Monday" in str(second.all_messages()[0].parts[0].content)  # type: ignore[union-attr]
        assert second.output == "noted"

    run_with_engine(tmp_path, scenario)


def load_synthetic_preferences(tmp_path: Path) -> list[MemoryPreference]:
    return load_preference_records(write_record_import(tmp_path) / "preferences.json")


def test_load_preference_records_reads_file_in_order(tmp_path: Path) -> None:
    preferences = load_synthetic_preferences(tmp_path)
    assert [p.preference_id for p in preferences] == ["pref_tone", "pref_report", "pref_rec_1002"]


def test_load_preference_records_rejects_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "preferences.json"
    path.write_text('[{"preference_id": "incomplete"}]')
    with pytest.raises(DataImportError, match="invalid_preferences"):
        load_preference_records(path)


def test_preference_memory_returns_active_tenant_and_record_preferences(tmp_path: Path) -> None:
    async def scenario() -> None:
        repository = InMemoryRecordRepository[MemoryPreference]()
        await repository.save_records(load_synthetic_preferences(tmp_path))
        memory = PreferenceMemory(repository, BEFORE_EXPIRY)
        tenant_wide = await memory.list_active_preferences(ALPHA)
        assert [p.preference_id for p in tenant_wide] == ["pref_report", "pref_tone"]
        with_record = await memory.list_active_preferences(ALPHA, record_id="REC-1002")
        assert len(with_record) == 3
        assert await memory.list_active_preferences(BETA) == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("update", "now"),
    [
        ({}, datetime(2027, 9, 20, 12, tzinfo=UTC)),
        ({"status": "revoked"}, BEFORE_EXPIRY.frozen_at),
        ({"status": "pending"}, BEFORE_EXPIRY.frozen_at),
        ({}, datetime(2026, 9, 1, tzinfo=UTC)),
    ],
    ids=["expired", "revoked", "pending", "not_yet_created"],
)
def test_preference_memory_excludes_inactive_preferences(
    tmp_path: Path, update: dict[str, str], now: datetime
) -> None:
    async def scenario() -> None:
        [preference, *_] = load_synthetic_preferences(tmp_path)
        repository = InMemoryRecordRepository[MemoryPreference]()
        await repository.save_records([preference.model_copy(update=update)])
        memory = PreferenceMemory(repository, FrozenClock(now))
        assert await memory.list_active_preferences(ALPHA) == []

    asyncio.run(scenario())


def test_sql_preferences_cannot_reference_another_tenants_record(tmp_path: Path) -> None:
    directory = write_record_import(tmp_path / "import")

    async def scenario(engine: AsyncEngine) -> None:
        await import_structured_data(directory, engine)
        repository = SqlRecordRepository(engine, memory_preferences, MemoryPreference)
        preferences = load_preference_records(directory / "preferences.json")
        assert await repository.save_records(preferences) == 3
        [note] = [p for p in preferences if p.record_id == "REC-1002"]
        foreign = note.model_copy(update={"tenant_id": "tenant_beta"})
        with pytest.raises(StorageError, match="integrity_violation"):
            await repository.save_records([foreign])

    run_with_engine(tmp_path, scenario)
