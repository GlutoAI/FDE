import asyncio
from collections.abc import Awaitable, Callable
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
from app.db.engine import build_database_url, open_database
from app.db.records import ExpenseRecord
from app.db.repository import (
    InMemoryRecordRepository,
    RecordRepository,
    SqlRecordRepository,
)
from app.db.tables import UtcDateTime, expenses, memory_preferences
from app.memory.preferences import MemoryPreference
from tests.synthetic import (
    ALPHA,
    BETA,
    SYNTHETIC_PREFERENCES,
    build_expense,
    write_expense_csv,
    write_expense_import,
)

GOOD_ROW = "tenant_alpha,EXP-1,user-1,Harbor Cafe,2026-09-02,2026-09-03,4250,USD,meals,,2026-09-20T12:00:00Z"


def run_with_engine(tmp_path: Path, scenario: Callable[[AsyncEngine], Awaitable[None]]) -> None:
    async def run_scenario() -> None:
        async with open_database(build_database_url(tmp_path, None)) as engine:
            await scenario(engine)

    asyncio.run(run_scenario())


RepositoryFactory = Callable[[AsyncEngine], RecordRepository[ExpenseRecord]]
REPOSITORY_FACTORIES: dict[str, RepositoryFactory] = {
    "memory": lambda engine: InMemoryRecordRepository[ExpenseRecord](),
    "sql": lambda engine: SqlRecordRepository(engine, expenses, ExpenseRecord),
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
            build_expense("EXP-2"),
            build_expense("EXP-1"),
            build_expense("EXP-9", "tenant_beta"),
        ]
        assert await repository.save_records(records) == 3
        assert await repository.get_record(ALPHA, "EXP-1") == records[1]
        listed = await repository.list_records(ALPHA, limit=10)
        assert [record.expense_id for record in listed] == ["EXP-1", "EXP-2"]
        assert len(await repository.list_records(ALPHA, limit=1)) == 1

    run_with_engine(tmp_path, scenario)


def test_repository_hides_other_tenants_records(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_expense("EXP-9", "tenant_beta")])
        with pytest.raises(RecordNotFoundError):
            await repository.get_record(ALPHA, "EXP-9")
        assert await repository.list_records(ALPHA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_repository_keeps_same_key_apart_across_tenants(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        alpha, beta = build_expense(), build_expense("EXP-1001", "tenant_beta", merchant="Other")
        assert await repository.save_records([alpha, beta]) == 2
        assert await repository.get_record(ALPHA, "EXP-1001") == alpha
        assert await repository.get_record(BETA, "EXP-1001") == beta

    run_with_engine(tmp_path, scenario)


def test_repository_save_is_idempotent_and_replaces_by_key(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_expense()])
        renamed = build_expense().model_copy(update={"merchant": "Renamed"})
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
        repository = SqlRecordRepository(engine, expenses, ExpenseRecord)
        await repository.save_records([build_expense(updated_at=eastern)])
        stored = await repository.get_record(ALPHA, "EXP-1001")
        assert stored.updated_at == eastern
        assert stored.updated_at.tzinfo == UTC

    run_with_engine(tmp_path, scenario)


def test_utc_datetime_column_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        UtcDateTime().process_bind_param(datetime(2026, 9, 26, 8, 0), sqlite.dialect())


def test_sql_repository_writes_nothing_when_one_record_fails(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await SqlRecordRepository(engine, expenses, ExpenseRecord).save_records([build_expense()])
        repository = SqlRecordRepository(engine, memory_preferences, MemoryPreference)
        valid = MemoryPreference.model_validate(SYNTHETIC_PREFERENCES[0], strict=False)
        orphan = valid.model_copy(update={"preference_id": "orphan", "expense_id": "EXP-MISSING"})
        with pytest.raises(StorageError, match="integrity_violation"):
            await repository.save_records([valid, orphan])
        assert await repository.list_records(ALPHA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_expense_record_rejects_posting_before_the_transaction() -> None:
    with pytest.raises(ValueError, match="posted_date"):
        build_expense(posted_date=date(2026, 9, 1))


def test_open_database_rejects_unknown_driver(tmp_path: Path) -> None:
    async def open_unknown() -> None:
        async with open_database("nosuchdb+driver:///x"):
            pass

    with pytest.raises(ConfigurationError, match="invalid_database_url"):
        asyncio.run(open_unknown())


def test_import_structured_data_loads_synthetic_csv_idempotently(tmp_path: Path) -> None:
    directory = write_expense_import(tmp_path / "import")

    async def scenario(engine: AsyncEngine) -> None:
        first = await import_structured_data(directory, engine)
        second = await import_structured_data(directory, engine)
        assert [(r.table, r.rows_read) for r in first] == [("expenses", 4)]
        assert first == second
        repository = SqlRecordRepository(engine, expenses, ExpenseRecord)
        [beta] = await repository.list_records(BETA, limit=500)
        assert (beta.expense_id, beta.merchant) == ("EXP-1001", "Summit Supplies")
        assert (await repository.get_record(ALPHA, "EXP-1001")).merchant == "Harbor Cafe"

    run_with_engine(tmp_path, scenario)


def write_raw_csv(path: Path, rows: list[str], header: str | None = None) -> Path:
    columns = header or ",".join(ExpenseRecord.model_fields)
    path.write_text("\n".join([columns, *rows]) + "\n")
    return path


def test_load_csv_records_reports_rows_and_fields_without_values(tmp_path: Path) -> None:
    bad = GOOD_ROW.replace(",4250,", ",SECRET-VALUE,")
    blank = GOOD_ROW.replace(",Harbor Cafe,", ",,")
    path = write_raw_csv(tmp_path / "expenses.csv", [GOOD_ROW, bad, blank])
    with pytest.raises(DataImportError) as failure:
        load_csv_records(path, ExpenseRecord)
    message = str(failure.value)
    assert "2 invalid rows" in message
    assert "line 3: amount_cents" in message
    assert "line 4: merchant" in message
    assert "SECRET-VALUE" not in message


def test_load_csv_records_parses_types_and_blank_receipt_from_text(tmp_path: Path) -> None:
    [record] = load_csv_records(write_raw_csv(tmp_path / "expenses.csv", [GOOD_ROW]), ExpenseRecord)
    assert (record.amount_cents, record.expense_date, record.receipt_id) == (
        4_250,
        date(2026, 9, 2),
        None,
    )


def test_load_csv_records_accepts_columns_in_any_order(tmp_path: Path) -> None:
    expected = build_expense()
    columns = list(reversed(ExpenseRecord.model_fields))
    row = expected.model_dump(mode="json")
    path = write_raw_csv(
        tmp_path / "expenses.csv",
        [",".join(str(row[column]) for column in columns)],
        header=",".join(columns),
    )
    assert load_csv_records(path, ExpenseRecord) == [expected]


@pytest.mark.parametrize(
    "header", ["expense_id,tenant_id,extra", ",".join([*ExpenseRecord.model_fields, "tenant_id"])]
)
def test_load_csv_records_rejects_mismatched_or_duplicated_header(
    tmp_path: Path, header: str
) -> None:
    path = write_raw_csv(tmp_path / "expenses.csv", [], header=header)
    with pytest.raises(DataImportError, match="invalid_csv_header"):
        load_csv_records(path, ExpenseRecord)


def test_load_csv_records_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DataImportError, match="unreadable_csv"):
        load_csv_records(tmp_path / "absent.csv", ExpenseRecord)


def test_import_structured_data_writes_nothing_when_any_row_is_invalid(tmp_path: Path) -> None:
    directory = tmp_path / "import"
    path = write_expense_csv(directory / "expenses.csv", [build_expense()])
    path.write_text(path.read_text() + "broken\n")

    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(DataImportError):
            await import_structured_data(directory, engine)
        repository = SqlRecordRepository(engine, expenses, ExpenseRecord)
        assert await repository.list_records(ALPHA, limit=500) == []

    run_with_engine(tmp_path, scenario)
