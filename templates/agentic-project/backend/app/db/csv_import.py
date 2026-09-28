"""Validate CSV files against record contracts and load them through repositories.

Every row of every file is validated before anything is written, so a bad file writes nothing.
Error messages name rows and fields only; they never echo cell values.
"""

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field, ValidationError
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.errors import DataImportError
from app.db.records import ExampleRecord, TenantRecord
from app.db.repository import RecordRepository, RecordT, SqlRecordRepository
from app.db.tables import example_records
from app.llm.contracts import Contract

MAX_REPORTED_PROBLEMS = 10


class ImportReport(Contract):
    """Outcome of importing one source file into one table."""

    table: str = Field(min_length=1, description="Destination table")
    source: str = Field(min_length=1, description="Source file name")
    rows_read: int = Field(ge=0, description="Data rows in the file")
    rows_written: int = Field(ge=0, description="Rows inserted or replaced")


# A dataclass, not a Contract: it holds a SQLAlchemy Table, which Pydantic cannot validate.
@dataclass(frozen=True)
class CsvTableSource:
    """A CSV file bound to its record contract and destination table.

    Attributes:
        file_name: File name inside the import directory.
        record_type: Contract every row must satisfy.
        table: Destination table whose columns match the contract's fields.
    """

    file_name: str
    record_type: type[TenantRecord]
    table: Table


# Parents must precede children so composite foreign keys resolve on first import.
STRUCTURED_SOURCES: tuple[CsvTableSource, ...] = (
    CsvTableSource("example_records.csv", ExampleRecord, example_records),
)


def load_csv_records(path: Path, record_type: type[RecordT]) -> list[RecordT]:
    """Read a CSV file and validate every row against a record contract.

    Empty cells become None, so optional fields can be left blank.

    Args:
        path: CSV file whose header matches the contract's field names exactly.
        record_type: Contract for each row; string cells are converted to its field types.

    Returns:
        One validated record per data row, in file order.

    Raises:
        DataImportError: The file is unreadable, its header differs from the contract, or any
            row is invalid. The message lists up to ``MAX_REPORTED_PROBLEMS`` rows and fields.
    """
    try:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            _validate_header(reader.fieldnames or [], record_type, path.name)
            return _parse_rows(reader, record_type, path.name)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise DataImportError(f"unreadable_csv: {path.name}") from error


async def import_csv_records(
    records: Sequence[RecordT], repository: RecordRepository[RecordT], source: CsvTableSource
) -> ImportReport:
    """Save already-validated records and report the counts.

    Args:
        records: Rows returned by ``load_csv_records``.
        repository: Destination storage; the write is atomic and idempotent.
        source: File and table the records came from, for the report.

    Returns:
        The rows read and written for this file.

    Raises:
        StorageError: The repository rejected the write.
    """
    rows_written = await repository.save_records(records)
    return ImportReport(
        table=source.table.name,
        source=source.file_name,
        rows_read=len(records),
        rows_written=rows_written,
    )


async def import_structured_data(
    structured_directory: Path, engine: AsyncEngine
) -> list[ImportReport]:
    """Validate every structured CSV, then write them in foreign-key order.

    Args:
        structured_directory: Directory containing the files in ``STRUCTURED_SOURCES``.
        engine: Database with the schema already created.

    Returns:
        One report per file, in import order.

    Raises:
        DataImportError: Any file is invalid; nothing is written.
        StorageError: A write failed; files written before it remain, and rerunning is safe.
    """
    loaded = [
        (source, load_csv_records(structured_directory / source.file_name, source.record_type))
        for source in STRUCTURED_SOURCES
    ]
    reports = []
    for source, records in loaded:
        repository = SqlRecordRepository(engine, source.table, source.record_type)
        reports.append(await import_csv_records(records, repository, source))
    return reports


def _validate_header(columns: Sequence[str], record_type: type[TenantRecord], name: str) -> None:
    """Raise unless the header names exactly the contract's fields, in any order.

    Args:
        columns: Header cells as read.
        record_type: Contract whose field names are required.
        name: File name, for the message.

    Raises:
        DataImportError: A field is missing, a column is unknown, or a column repeats.
    """
    expected = set(record_type.model_fields)
    missing, unknown = sorted(expected - set(columns)), sorted(set(columns) - expected)
    if missing or unknown or len(columns) != len(set(columns)):
        raise DataImportError(
            f"invalid_csv_header: {name}: missing={missing} unknown={unknown} or duplicated"
        )


def _parse_rows(rows: csv.DictReader[str], record_type: type[RecordT], name: str) -> list[RecordT]:
    """Validate each row, collecting problems so one error report covers the whole file.

    Args:
        rows: Reader positioned after the header.
        record_type: Contract each row must satisfy.
        name: File name, for the message.

    Returns:
        One record per row, in file order.

    Raises:
        DataImportError: Any row is invalid; lists up to ``MAX_REPORTED_PROBLEMS`` of them.
    """
    records: list[RecordT] = []
    problems: list[str] = []
    # Line 1 is the header, so the first data row is line 2 in an editor.
    for line_number, row in enumerate(rows, start=2):
        cells = {column: (value if value != "" else None) for column, value in row.items()}
        try:
            # Records are strict by default; CSV cells are text, so allow "4250" -> 4250 here.
            records.append(record_type.model_validate(cells, strict=False))
        except ValidationError as error:
            problems.append(_format_row_problem(line_number, error))
    if problems:
        shown = "; ".join(problems[:MAX_REPORTED_PROBLEMS])
        raise DataImportError(f"invalid_csv_rows: {name}: {len(problems)} invalid rows: {shown}")
    return records


def _format_row_problem(line_number: int, error: ValidationError) -> str:
    """Describe a row's failures by field and error type, without the offending values.

    Args:
        line_number: One-based line of the row in the file.
        error: Pydantic's validation failure for that row.

    Returns:
        For example ``line 3: amount_cents (int_parsing)``; ``row`` names a cross-field rule.
    """
    fields = sorted(
        f"{'.'.join(str(part) for part in item['loc']) or 'row'} ({item['type']})"
        for item in error.errors()
    )
    return f"line {line_number}: {', '.join(fields)}"
