"""Verify tenant-scoped repositories, the schema, and CSV import; one suite runs on both stores."""

import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.errors import (
    ConfigurationError,
    DataImportError,
    InvalidQueryError,
    RecordNotFoundError,
    StorageError,
)
from app.db.csv_import import import_structured_data, load_csv_records
from app.db.engine import open_database
from app.db.records import ExampleRecord
from app.db.repository import (
    InMemoryRecordRepository,
    RecordRepository,
    SqlRecordRepository,
)
from app.db.tables import UtcDateTime, example_records, memory_preferences
from app.memory.preferences import MemoryPreference
from tests.synthetic import (
    ALPHA,
    BETA,
    RECORDS_FILE,
    SYNTHETIC_PREFERENCES,
    build_record,
    run_with_engine,
    write_record_import,
    write_records_csv,
)

GOOD_ROW = "tenant_alpha,REC-1,user-1,Harbor Cafe,meals,4250,USD,2026-09-02,,2026-09-20T12:00:00Z"


RepositoryFactory = Callable[[AsyncEngine], RecordRepository[ExampleRecord]]
REPOSITORY_FACTORIES: dict[str, RepositoryFactory] = {
    "memory": lambda engine: InMemoryRecordRepository[ExampleRecord](),
    "sql": lambda engine: SqlRecordRepository(engine, example_records, ExampleRecord),
}


@pytest.fixture(params=sorted(REPOSITORY_FACTORIES))
def repository_factory(request: pytest.FixtureRequest) -> RepositoryFactory:
    return REPOSITORY_FACTORIES[request.param]


def test_repository_saves_and_reads_records_by_tenant(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        records = [
            build_record("REC-2"),
            build_record("REC-1"),
            build_record("REC-9", "tenant_beta"),
        ]
        assert await repository.save_records(records) == 3
        assert await repository.get_record(ALPHA, "REC-1") == records[1]
        listed = await repository.list_records(ALPHA, limit=10)
        assert [record.record_id for record in listed] == ["REC-1", "REC-2"]
        assert len(await repository.list_records(ALPHA, limit=1)) == 1

    run_with_engine(tmp_path, scenario)


def test_repository_hides_other_tenants_records(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_record("REC-9", "tenant_beta")])
        with pytest.raises(RecordNotFoundError):
            await repository.get_record(ALPHA, "REC-9")
        assert await repository.list_records(ALPHA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_repository_keeps_same_key_apart_across_tenants(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        alpha, beta = build_record(), build_record("REC-1001", "tenant_beta", name="Other")
        assert await repository.save_records([alpha, beta]) == 2
        assert await repository.get_record(ALPHA, "REC-1001") == alpha
        assert await repository.get_record(BETA, "REC-1001") == beta

    run_with_engine(tmp_path, scenario)


def test_repository_save_is_idempotent_and_replaces_by_key(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_record()])
        renamed = build_record().model_copy(update={"name": "Renamed"})
        await repository.save_records([renamed])
        await repository.save_records([renamed])
        assert await repository.list_records(ALPHA, limit=10) == [renamed]

    run_with_engine(tmp_path, scenario)


@pytest.mark.parametrize("limit", [0, 501])
def test_repository_rejects_unbounded_list_limit(
    tmp_path: Path, repository_factory: RepositoryFactory, limit: int
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(InvalidQueryError):
            await repository_factory(engine).list_records(ALPHA, limit=limit)

    run_with_engine(tmp_path, scenario)


def test_sql_repository_round_trips_aware_datetime_as_same_instant(tmp_path: Path) -> None:
    eastern = datetime(2026, 9, 26, 8, 0, tzinfo=timezone(timedelta(hours=-4)))

    async def scenario(engine: AsyncEngine) -> None:
        repository = SqlRecordRepository(engine, example_records, ExampleRecord)
        await repository.save_records([build_record(updated_at=eastern)])
        stored = await repository.get_record(ALPHA, "REC-1001")
        assert stored.updated_at == eastern
        assert stored.updated_at.tzinfo == UTC

    run_with_engine(tmp_path, scenario)


def test_utc_datetime_column_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        UtcDateTime().process_bind_param(datetime(2026, 9, 26, 8, 0), sqlite.dialect())


def test_sql_repository_writes_nothing_when_one_record_fails(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await SqlRecordRepository(engine, example_records, ExampleRecord).save_records(
            [build_record()]
        )
        repository = SqlRecordRepository(engine, memory_preferences, MemoryPreference)
        valid = MemoryPreference.model_validate(SYNTHETIC_PREFERENCES[0], strict=False)
        orphan = valid.model_copy(update={"preference_id": "orphan", "record_id": "REC-MISSING"})
        with pytest.raises(StorageError, match="integrity_violation"):
            await repository.save_records([valid, orphan])
        assert await repository.list_records(ALPHA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_example_record_rejects_closing_before_opening() -> None:
    with pytest.raises(ValueError, match="closed_on"):
        build_record(closed_on=date(2026, 9, 1))


def test_open_database_rejects_unknown_driver(tmp_path: Path) -> None:
    async def open_unknown() -> None:
        async with open_database("nosuchdb+driver:///x"):
            pass

    with pytest.raises(ConfigurationError, match="invalid_database_url"):
        asyncio.run(open_unknown())


def test_import_structured_data_loads_synthetic_csv_idempotently(tmp_path: Path) -> None:
    directory = write_record_import(tmp_path / "import")

    async def scenario(engine: AsyncEngine) -> None:
        first = await import_structured_data(directory, engine)
        second = await import_structured_data(directory, engine)
        assert [(r.table, r.rows_read) for r in first] == [("example_records", 4)]
        assert first == second
        repository = SqlRecordRepository(engine, example_records, ExampleRecord)
        [beta] = await repository.list_records(BETA, limit=500)
        assert (beta.record_id, beta.name) == ("REC-1001", "Summit Supplies")
        assert (await repository.get_record(ALPHA, "REC-1001")).name == "Harbor Cafe"

    run_with_engine(tmp_path, scenario)


def write_raw_csv(path: Path, rows: list[str], header: str | None = None) -> Path:
    """Write CSV lines verbatim, for malformed files ``write_records_csv`` cannot produce."""
    columns = header or ",".join(ExampleRecord.model_fields)
    path.write_text("\n".join([columns, *rows]) + "\n")
    return path


def test_load_csv_records_reports_rows_and_fields_without_values(tmp_path: Path) -> None:
    bad = GOOD_ROW.replace(",4250,", ",SECRET-VALUE,")
    blank = GOOD_ROW.replace(",Harbor Cafe,", ",,")
    path = write_raw_csv(tmp_path / RECORDS_FILE, [GOOD_ROW, bad, blank])
    with pytest.raises(DataImportError) as failure:
        load_csv_records(path, ExampleRecord)
    message = str(failure.value)
    assert "2 invalid rows" in message
    assert "line 3: amount_cents" in message
    assert "line 4: name" in message
    assert "SECRET-VALUE" not in message


def test_load_csv_records_parses_types_and_blank_optional_from_text(tmp_path: Path) -> None:
    [record] = load_csv_records(write_raw_csv(tmp_path / RECORDS_FILE, [GOOD_ROW]), ExampleRecord)
    assert (record.amount_cents, record.opened_on, record.closed_on) == (
        4_250,
        date(2026, 9, 2),
        None,
    )


def test_load_csv_records_accepts_columns_in_any_order(tmp_path: Path) -> None:
    expected = build_record()
    columns = list(reversed(ExampleRecord.model_fields))
    row = expected.model_dump(mode="json")
    path = write_raw_csv(
        tmp_path / RECORDS_FILE,
        [",".join(str(row[column]) for column in columns)],
        header=",".join(columns),
    )
    assert load_csv_records(path, ExampleRecord) == [expected]


@pytest.mark.parametrize(
    "header", ["record_id,tenant_id,extra", ",".join([*ExampleRecord.model_fields, "tenant_id"])]
)
def test_load_csv_records_rejects_mismatched_or_duplicated_header(
    tmp_path: Path, header: str
) -> None:
    path = write_raw_csv(tmp_path / RECORDS_FILE, [], header=header)
    with pytest.raises(DataImportError, match="invalid_csv_header"):
        load_csv_records(path, ExampleRecord)


def test_load_csv_records_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DataImportError, match="unreadable_csv"):
        load_csv_records(tmp_path / "absent.csv", ExampleRecord)


def test_import_structured_data_writes_nothing_when_any_row_is_invalid(tmp_path: Path) -> None:
    directory = tmp_path / "import"
    path = write_records_csv(directory / RECORDS_FILE, [build_record()])
    path.write_text(path.read_text() + "broken\n")

    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(DataImportError):
            await import_structured_data(directory, engine)
        repository = SqlRecordRepository(engine, example_records, ExampleRecord)
        assert await repository.list_records(ALPHA, limit=500) == []

    run_with_engine(tmp_path, scenario)
