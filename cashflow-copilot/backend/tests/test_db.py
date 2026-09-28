import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.dialects import sqlite
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.context import TenantScope
from app.core.errors import (
    ConfigurationError,
    DataImportError,
    InvalidQueryError,
    RecordNotFoundError,
    StorageError,
)
from app.db.csv_import import import_structured_data, load_csv_records
from app.db.engine import build_database_url, open_database
from app.db.records import CustomerRecord, InvoiceRecord
from app.db.repository import (
    InMemoryRecordRepository,
    RecordRepository,
    SqlRecordRepository,
)
from app.db.tables import UtcDateTime, customers, invoices

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
AURORA = TenantScope(tenant_id="tenant_aurora")
COPPER = TenantScope(tenant_id="tenant_copper")


def build_customer(customer_id: str = "CUS-1", tenant_id: str = "tenant_aurora") -> CustomerRecord:
    return CustomerRecord(
        tenant_id=tenant_id,
        customer_id=customer_id,
        display_name="Harbor & Pine Retail",
        contact_name="Alex Morgan",
        email="billing@example.test",
        payment_terms_days=30,
        currency="USD",
        active=True,
    )


def build_invoice(
    customer_id: str = "CUS-1", tenant_id: str = "tenant_aurora", paid_cents: int = 0
) -> InvoiceRecord:
    return InvoiceRecord(
        tenant_id=tenant_id,
        invoice_id="INV-1",
        customer_id=customer_id,
        invoice_number="SYN-1",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 30),
        currency="USD",
        subtotal_cents=10_000,
        tax_cents=0,
        total_cents=10_000,
        paid_cents=paid_cents,
        balance_cents=10_000 - paid_cents,
        status="open",
        disputed_cents=0,
        source_system="synthetic_qbo",
        external_id="ext-1",
        updated_at=datetime(2026, 9, 26, 8, 0, tzinfo=timezone(timedelta(hours=-4))),
    )


def run_with_engine(tmp_path: Path, scenario: Callable[[AsyncEngine], Awaitable[None]]) -> None:
    async def run_scenario() -> None:
        async with open_database(build_database_url(tmp_path, None)) as engine:
            await scenario(engine)

    asyncio.run(run_scenario())


RepositoryFactory = Callable[[AsyncEngine], RecordRepository[CustomerRecord]]
REPOSITORY_FACTORIES: dict[str, RepositoryFactory] = {
    "memory": lambda engine: InMemoryRecordRepository[CustomerRecord](),
    "sql": lambda engine: SqlRecordRepository(engine, customers, CustomerRecord),
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
            build_customer("CUS-2"),
            build_customer("CUS-1"),
            build_customer("CUS-9", "tenant_copper"),
        ]
        assert await repository.save_records(records) == 3
        assert await repository.get_record(AURORA, "CUS-1") == records[1]
        listed = await repository.list_records(AURORA, limit=10)
        assert [record.customer_id for record in listed] == ["CUS-1", "CUS-2"]
        assert len(await repository.list_records(AURORA, limit=1)) == 1

    run_with_engine(tmp_path, scenario)


def test_repository_hides_other_tenants_records(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_customer("CUS-9", "tenant_copper")])
        with pytest.raises(RecordNotFoundError):
            await repository.get_record(AURORA, "CUS-9")
        assert await repository.list_records(AURORA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_repository_save_is_idempotent_and_replaces_by_key(
    tmp_path: Path, repository_factory: RepositoryFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        repository = repository_factory(engine)
        await repository.save_records([build_customer()])
        renamed = build_customer().model_copy(update={"display_name": "Renamed"})
        await repository.save_records([renamed])
        await repository.save_records([renamed])
        assert await repository.list_records(AURORA, limit=10) == [renamed]

    run_with_engine(tmp_path, scenario)


@pytest.mark.parametrize("limit", [0, 501])
def test_repository_rejects_unbounded_list_limit(
    tmp_path: Path, repository_factory: RepositoryFactory, limit: int
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(InvalidQueryError):
            await repository_factory(engine).list_records(AURORA, limit=limit)

    run_with_engine(tmp_path, scenario)


def test_sql_repository_round_trips_aware_datetime_as_same_instant(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await SqlRecordRepository(engine, customers, CustomerRecord).save_records(
            [build_customer()]
        )
        repository = SqlRecordRepository(engine, invoices, InvoiceRecord)
        await repository.save_records([build_invoice()])
        stored = await repository.get_record(AURORA, "INV-1")
        assert stored.updated_at == build_invoice().updated_at
        assert stored.updated_at.tzinfo == UTC

    run_with_engine(tmp_path, scenario)


def test_utc_datetime_column_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="naive"):
        UtcDateTime().process_bind_param(datetime(2026, 9, 26, 8, 0), sqlite.dialect())


def test_sql_repository_rejects_reference_to_another_tenants_customer(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await SqlRecordRepository(engine, customers, CustomerRecord).save_records(
            [build_customer("CUS-1", "tenant_copper")]
        )
        with pytest.raises(StorageError, match="integrity_violation"):
            await SqlRecordRepository(engine, invoices, InvoiceRecord).save_records(
                [build_invoice()]
            )

    run_with_engine(tmp_path, scenario)


def test_sql_repository_writes_nothing_when_one_record_fails(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        await SqlRecordRepository(engine, customers, CustomerRecord).save_records(
            [build_customer()]
        )
        repository = SqlRecordRepository(engine, invoices, InvoiceRecord)
        orphan = build_invoice(customer_id="CUS-MISSING").model_copy(update={"invoice_id": "INV-2"})
        with pytest.raises(StorageError):
            await repository.save_records([build_invoice(), orphan])
        assert await repository.list_records(AURORA, limit=10) == []

    run_with_engine(tmp_path, scenario)


def test_invoice_record_rejects_inconsistent_balance() -> None:
    values = build_invoice().model_dump() | {"balance_cents": 1}
    with pytest.raises(ValueError, match="balance_cents"):
        InvoiceRecord.model_validate(values)


def test_open_database_rejects_unknown_driver(tmp_path: Path) -> None:
    async def open_unknown() -> None:
        async with open_database("nosuchdb+driver:///x"):
            pass

    with pytest.raises(ConfigurationError, match="invalid_database_url"):
        asyncio.run(open_unknown())


def test_import_structured_data_loads_synthetic_csv_idempotently(tmp_path: Path) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        first = await import_structured_data(DATA_ROOT / "structured", engine)
        second = await import_structured_data(DATA_ROOT / "structured", engine)
        assert [(r.table, r.rows_read) for r in first] == [("customers", 15), ("invoices", 53)]
        assert first == second
        stored = await SqlRecordRepository(engine, invoices, InvoiceRecord).list_records(
            COPPER, limit=500
        )
        assert stored and {record.tenant_id for record in stored} == {"tenant_copper"}

    run_with_engine(tmp_path, scenario)


def write_customer_csv(path: Path, rows: list[str], header: str | None = None) -> Path:
    columns = header or ",".join(CustomerRecord.model_fields)
    path.write_text("\n".join([columns, *rows]) + "\n")
    return path


def test_load_csv_records_reports_rows_and_fields_without_values(tmp_path: Path) -> None:
    good = "tenant_aurora,CUS-1,Harbor,Alex,a@example.test,30,USD,true"
    bad = "tenant_aurora,CUS-2,Summit,Jamie,a@example.test,SECRET-VALUE,USD,true"
    blank = "tenant_aurora,CUS-3,,Taylor,a@example.test,30,USD,true"
    path = write_customer_csv(tmp_path / "customers.csv", [good, bad, blank])
    with pytest.raises(DataImportError) as failure:
        load_csv_records(path, CustomerRecord)
    message = str(failure.value)
    assert "2 invalid rows" in message
    assert "line 3: payment_terms_days" in message
    assert "line 4: display_name" in message
    assert "SECRET-VALUE" not in message


def test_load_csv_records_parses_types_from_text(tmp_path: Path) -> None:
    path = write_customer_csv(
        tmp_path / "customers.csv", ["tenant_aurora,CUS-1,Harbor,Alex,a@example.test,45,USD,false"]
    )
    [record] = load_csv_records(path, CustomerRecord)
    assert (record.payment_terms_days, record.active) == (45, False)


def test_load_csv_records_rejects_mismatched_header(tmp_path: Path) -> None:
    path = write_customer_csv(tmp_path / "customers.csv", [], header="customer_id,tenant_id,extra")
    with pytest.raises(DataImportError, match="invalid_csv_header"):
        load_csv_records(path, CustomerRecord)


def test_load_csv_records_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DataImportError, match="unreadable_csv"):
        load_csv_records(tmp_path / "absent.csv", CustomerRecord)


def test_import_structured_data_writes_nothing_when_a_later_file_is_invalid(
    tmp_path: Path,
) -> None:
    structured = tmp_path / "structured"
    structured.mkdir()
    (structured / "customers.csv").write_text((DATA_ROOT / "structured/customers.csv").read_text())
    (structured / "invoices.csv").write_text(",".join(InvoiceRecord.model_fields) + "\nbroken\n")

    async def scenario(engine: AsyncEngine) -> None:
        with pytest.raises(DataImportError):
            await import_structured_data(structured, engine)
        repository = SqlRecordRepository(engine, customers, CustomerRecord)
        assert await repository.list_records(AURORA, limit=500) == []

    run_with_engine(tmp_path, scenario)
