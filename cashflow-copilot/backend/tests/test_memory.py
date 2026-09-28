import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.test import TestModel
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.clock import FrozenClock, SystemClock
from app.core.context import TenantScope
from app.core.errors import AccessDeniedError, InvalidQueryError, StorageError
from app.db.csv_import import import_structured_data
from app.db.engine import build_database_url, open_database
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

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
AURORA = TenantScope(tenant_id="tenant_aurora")
COPPER = TenantScope(tenant_id="tenant_copper")
BEFORE_EXPIRY = FrozenClock(datetime(2026, 9, 27, tzinfo=UTC))


def build_exchange(number: int) -> list[ModelMessage]:
    return [
        ModelRequest(parts=[UserPromptPart(content=f"question {number}")]),
        ModelResponse(parts=[TextPart(content=f"answer {number}")]),
    ]


def read_texts(messages: list[ModelMessage]) -> list[str]:
    return [str(part.content) for message in messages for part in message.parts]  # type: ignore[union-attr]


def run_with_engine(tmp_path: Path, scenario: Callable[[AsyncEngine], Awaitable[None]]) -> None:
    async def run_scenario() -> None:
        async with open_database(build_database_url(tmp_path, None)) as engine:
            await scenario(engine)

    asyncio.run(run_scenario())


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
        assert await store.save_messages(AURORA, "thread-1", build_exchange(1)) == 2
        await store.save_messages(AURORA, "thread-1", build_exchange(2))
        everything = await store.load_messages(AURORA, "thread-1", limit=10)
        assert read_texts(everything) == ["question 1", "answer 1", "question 2", "answer 2"]
        window = await store.load_messages(AURORA, "thread-1", limit=2)
        assert read_texts(window) == ["question 2", "answer 2"]
        assert await store.load_messages(AURORA, "unknown-thread", limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_conversation_store_denies_other_tenant_reads_and_writes(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        store = store_factory(engine)
        await store.save_messages(AURORA, "thread-1", build_exchange(1))
        with pytest.raises(AccessDeniedError):
            await store.load_messages(COPPER, "thread-1", limit=10)
        with pytest.raises(AccessDeniedError):
            await store.save_messages(COPPER, "thread-1", build_exchange(2))
        assert len(await store.load_messages(AURORA, "thread-1", limit=10)) == 2

    run_with_engine(tmp_path, scenario)


@pytest.mark.parametrize("limit", [0, 201])
def test_conversation_store_rejects_unbounded_history(
    tmp_path: Path, store_factory: StoreFactory, limit: int
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(InvalidQueryError):
            await store_factory(engine).load_messages(AURORA, "thread-1", limit=limit)

    run_with_engine(tmp_path, scenario)


def test_sql_conversation_history_feeds_a_later_agent_run(tmp_path: Path) -> None:
    agent = Agent(TestModel(custom_output_text="noted"), instructions="Remember the thread.")

    async def scenario(engine: AsyncEngine) -> None:
        store = SqlConversationStore(engine)
        first = await agent.run("My preferred report day is Monday.")
        await store.save_messages(AURORA, "thread-1", first.new_messages())
        history = await store.load_messages(AURORA, "thread-1", limit=50)
        second = await agent.run("What did I say?", message_history=history)
        assert "Monday" in str(second.all_messages()[0].parts[0].content)  # type: ignore[union-attr]
        assert second.output == "noted"

    run_with_engine(tmp_path, scenario)


def test_load_preference_records_reads_synthetic_preferences() -> None:
    preferences = load_preference_records(DATA_ROOT / "memory/preferences.json")
    assert [p.preference_id for p in preferences] == [
        "memory_tone",
        "memory_harbor",
        "memory_report",
    ]


def test_preference_memory_returns_active_tenant_and_customer_preferences() -> None:
    async def scenario() -> None:
        repository = InMemoryRecordRepository[MemoryPreference]()
        await repository.save_records(
            load_preference_records(DATA_ROOT / "memory/preferences.json")
        )
        memory = PreferenceMemory(repository, BEFORE_EXPIRY)
        tenant_wide = await memory.list_active_preferences(AURORA)
        assert [p.preference_id for p in tenant_wide] == ["memory_report", "memory_tone"]
        with_customer = await memory.list_active_preferences(AURORA, customer_id="CUS-A-001")
        assert len(with_customer) == 3
        assert await memory.list_active_preferences(COPPER) == []

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
    update: dict[str, str], now: datetime
) -> None:
    async def scenario() -> None:
        [preference, *_] = load_preference_records(DATA_ROOT / "memory/preferences.json")
        repository = InMemoryRecordRepository[MemoryPreference]()
        await repository.save_records([preference.model_copy(update=update)])
        memory = PreferenceMemory(repository, FrozenClock(now))
        assert await memory.list_active_preferences(AURORA) == []

    asyncio.run(scenario())


def test_sql_preferences_cannot_reference_another_tenants_customer(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await import_structured_data(DATA_ROOT / "structured", engine)
        repository = SqlRecordRepository(engine, memory_preferences, MemoryPreference)
        preferences = load_preference_records(DATA_ROOT / "memory/preferences.json")
        assert await repository.save_records(preferences) == 3
        [harbor] = [p for p in preferences if p.customer_id == "CUS-A-001"]
        foreign = harbor.model_copy(update={"tenant_id": "tenant_copper"})
        with pytest.raises(StorageError, match="integrity_violation"):
            await repository.save_records([foreign])

    run_with_engine(tmp_path, scenario)
