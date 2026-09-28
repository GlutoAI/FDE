# Coding Standards

Detailed reference for [`.cursor/skills/coding-standards/SKILL.md`](../../.cursor/skills/coding-standards/SKILL.md). The skill holds the rules; this page holds the reasoning and worked examples.

Scope: all application code in the workspace, including `backend/`, `frontend/`, and each project's `src/`. Standalone data scripts such as `cashflow-copilot/scripts/` are exempt. A project's own plan decides paths, database, and test layout, and the scaffold traps apply only to `backend/` and `frontend/`. The skill's Scope section is authoritative.

## Why these rules

The rules optimize for one thing: code that a reviewer can verify is correct by reading it, without running it.

- **Names** say what a function does and what a variable holds, so a call site can be read without opening the definition.
- **Docstrings** state intent and contract, so behavior can be checked against them.
- **Single responsibility** keeps the unit of verification small.
- **Pydantic models** make the contract between modules explicit and enforced at runtime.
- **Abstract base classes** make the contract between a caller and its collaborators explicit and enforced at construction.
- **Tests** pin the behavior, so a later change cannot silently break it.

## Thresholds, and why those numbers

| Rule | Limit | Reasoning |
|------|-------|-----------|
| Function body | 30 lines | Fits on one screen; beyond this a named sub-step is hiding inside |
| Nesting depth | 3 levels | Each level multiplies the paths a reader must hold in their head |
| Positional parameters | 4 | More arguments means they form a concept that deserves a model |
| Behaviors per test | 1 | A failing test should identify one cause, not several |

Treat these as tripwires rather than laws. Crossing one is a prompt to look for the extraction you are missing, and occasionally the honest answer is that the function is genuinely a flat 35-line sequence. Document the reason in that case.

## Naming, and why verb-first

A function is an action, so its name is an action: `calculate_runway(forecast)` reads as a sentence, while `runway(forecast)` could be a getter, a constructor, or a calculation. Variables and classes are things, so they are nouns. Following that split mechanically settles most naming arguments.

The verb lexicon exists because synonyms hide semantics. If `get_invoice` and `fetch_invoice` both mean "look up an invoice," a reader cannot tell which one raises and which returns `None`. So the lexicon assigns each verb one meaning:
- `get_` raises when the thing is absent.
- `find_` returns `None`.
- `list_` returns a possibly empty list.
- `fetch_` crosses the network.
- `calculate_` and `build_` do no I/O.
- `is_`/`has_`/`can_`/`should_` return a `bool` with no side effects.

A caller can then handle the result correctly from the name alone. When no lexicon verb fits, choose a precise verb and use it with one meaning everywhere, rather than stretching an existing verb.

Renames the standard implies for existing code, applied when the code is next touched rather than in a separate sweep:

| Before | After | Why |
|---|---|---|
| `health_check()` | `check_health()` | Verb first |
| `data`, `result`, `info` | `invoice`, `forecast`, `health_report` | Name what it holds |
| `invoice_list` | `invoices` | No type in the name |
| `valid`, `overdue` (booleans) | `is_valid`, `is_overdue` | Booleans read as questions |
| `timeout` | `timeout_seconds` | Quantities carry their unit |

Casing follows PEP 8 and the Google Python and TypeScript guides. Two deliberate departures:
- TypeScript file names follow the frontend's existing camelCase and PascalCase files (`client.ts`, `App.tsx`) rather than Google's `snake_case`, because consistency with the codebase wins.
- Python acronyms stay upper case in class names (`HTTPClient`), per PEP 8, while TypeScript treats them as words (`HttpClient`), per the Google TypeScript guide.

## Docstrings: what "complete" means

A docstring is complete when a caller can use the thing correctly without reading its body. That means every parameter's meaning, units, and constraints; what comes back, including the empty and `None` cases; every exception deliberately raised and when; and every side effect. The signature cannot say any of these things.

Three placements matter most:

- **Class docstrings** describe what an instance *represents* ("A repository of invoices stored in SQLite."), because a class is a noun. List public attributes under `Attributes:`.
- **Abstract method docstrings** are the contract that every implementation, including the test fake, must honor. This is where Liskov substitution becomes checkable: a reviewer compares each implementation against the docstring.
- **Overrides** carry `@typing.override` and no docstring when they match the contract, so the contract lives in one place. They get a docstring only when they refine it.

Exception docstrings describe what the error *represents* ("No invoice exists with the requested ID."), not where it is raised, because the same exception is raised from many places.

## Worked example: the health endpoint

The existing `app/routers/health.py` is the codebase as it stands, before the standards were adopted. It is a useful example precisely because it is small and still violates several rules.

### Current

```python
@router.get("/health")
def health_check():
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "db": "disconnected", "detail": str(e)},
        )
```

Five problems. The name `health_check` is a noun phrase, not a verb. There is no docstring. The return type is an unvalidated dict rather than a model, so nothing enforces the shape and FastAPI cannot document it. The function mixes two responsibilities — probing the database and translating the result into an HTTP response — which means testing the probe requires going through the web layer. And `except Exception` swallows everything, including bugs in the handler itself.

### To the standard

Schema in `app/schemas/health.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Reported health of the API and its database."""

    status: Literal["ok", "error"] = Field(description="Overall health of the API")
    db: Literal["connected", "disconnected"] = Field(description="Database reachability")
    detail: str | None = Field(
        default=None, description="Error text, present only when status is error"
    )
```

Probe in `app/services/health.py`, with no knowledge of HTTP:

```python
def probe_database() -> HealthResponse:
    """Check that the database accepts queries.

    Returns:
        A report with status "ok" when the probe succeeds, otherwise
        status "error" with the failure text in ``detail``.
    """
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
    except sqlite3.Error as exc:
        return HealthResponse(status="error", db="disconnected", detail=str(exc))
    return HealthResponse(status="ok", db="connected")
```

Route in `app/routers/health.py`, which only translates to HTTP:

```python
@router.get("/health", response_model=HealthResponse)
def check_health() -> HealthResponse:
    """Report API and database health.

    Returns:
        The health report when the database is reachable.

    Raises:
        HTTPException: 503 when the database probe fails.
    """
    report = probe_database()
    if report.status == "error":
        raise HTTPException(status_code=503, detail=report.model_dump())
    return report
```

Each function now does one thing and is named for it, the contract is a validated model that appears in the OpenAPI schema, `sqlite3.Error` is caught rather than everything, and `probe_database` is testable without an HTTP client.

### Its tests

```python
def test_probe_database_reports_connected_when_query_succeeds(tmp_path):
    # Arrange
    configure_database(tmp_path / "test.db")

    # Act
    result = probe_database()

    # Assert
    assert result.status == "ok"
    assert result.db == "connected"


def test_probe_database_reports_error_when_database_is_unreachable(monkeypatch):
    # Arrange
    monkeypatch.setattr(
        "app.services.health.get_db_connection",
        _raising(sqlite3.OperationalError("unable to open database file")),
    )

    # Act
    result = probe_database()

    # Assert
    assert result.status == "error"
    assert "unable to open database file" in result.detail
```

The names state the behavior, so a failure in CI is legible without opening the file.

## Test layout

Mirror the source tree:

```
backend/
├── app/
│   ├── routers/health.py
│   └── services/health.py
└── tests/
    ├── conftest.py            # shared fixtures
    ├── routers/test_health.py
    └── services/test_health.py
```

Put the SQLite fixture in `conftest.py` and back it with `tmp_path` so each test gets a fresh database and the suite can run in parallel. Route tests use FastAPI's `TestClient`; service tests call the function directly.

### Not yet set up

There is no test suite in the repository today, and `requirements.txt` contains only `fastapi` and `uvicorn`. Running tests requires:

```bash
cd backend
source venv/bin/activate
python -m pip install pytest httpx
```

`httpx` is needed by FastAPI's `TestClient`. These belong in a `requirements-dev.txt` once the suite exists.

## Pydantic scope

The rule is that every function crossing a module boundary takes a model and returns a model. The exemption is module-private helpers prefixed `_` and used only in their own file.

The reasoning: models buy validation and a self-documenting contract at the points where a wrong shape would otherwise surface far from its cause. Within a single file the author can see both sides of the call, so the model costs indirection without buying safety. At a boundary, they cannot.

Two places where a model is always worth it regardless of the boundary rule: anything reaching the database, and anything derived from user input.

## Object-oriented design

### When a class, and when not

The scaffold's current code is entirely functions, which is correct for its size. Introduce a class when you have state plus behavior over that state, such as a repository holding a connection or a client holding configuration. Also introduce one when you need a substitutable implementation of an abstraction. Do not introduce a class to group functions that share a prefix; that is what modules are for.

### Why `abc.ABC` rather than `typing.Protocol` for our own abstractions

Both let a caller depend on a contract instead of a concrete class. They fail differently:

| | `abc.ABC` | `typing.Protocol` |
|---|---|---|
| Relationship | Nominal: implementations declare `class X(Contract)` | Structural: anything with matching members fits |
| Missing method | `TypeError` when the class is instantiated | Caught only by a type checker; at runtime, only when the method is called |
| Readability | "What implements this?" is one search for the base name | Implementations are invisible until a checker connects them |
| Shared implementation | Can hold concrete template methods | Should not |
| Works on types we don't own | No, since we can't make them inherit | Yes |

This repository has no type checker installed yet, so the ABC's runtime `TypeError` is the only guarantee that actually runs. The explicit `class SqliteInvoiceRepository(InvoiceRepository)` line also documents the relationship where a reader will see it.

The cost is that an implementation must import its ABC. That is no cost at all when we own both sides. `Protocol` keeps the two cases where that coupling is impossible or pointless:
- Describing a third-party object we accept.
- A callback signature.

### Worked example: a repository, its fake, and a contract test

```python
class UserRepository(ABC):
    """A store of user records, substitutable so services can be tested without a database."""

    @abstractmethod
    def get_user(self, user_id: str) -> User:
        """Return the user with the given ID.

        Args:
            user_id: Identifier of an existing user.

        Returns:
            The stored user.

        Raises:
            UserNotFoundError: If no user has that ID.
        """

    @abstractmethod
    def save_user(self, user: User) -> None:
        """Insert the user, or replace the stored user with the same ID.

        Args:
            user: The user to persist.
        """


class SqliteUserRepository(UserRepository):
    """A store of user records in SQLite.

    Attributes:
        connection: Open connection used for every query; the caller owns its lifecycle.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @override
    def get_user(self, user_id: str) -> User:
        row = self.connection.execute(SELECT_USER_SQL, (user_id,)).fetchone()
        if row is None:
            raise UserNotFoundError(user_id)
        return User.from_row(row)

    @override
    def save_user(self, user: User) -> None:
        self.connection.execute(UPSERT_USER_SQL, user.to_row())
        self.connection.commit()


class InMemoryUserRepository(UserRepository):
    """A store of user records in a dict, for tests."""

    def __init__(self) -> None:
        self._user_by_id: dict[str, User] = {}

    @override
    def get_user(self, user_id: str) -> User:
        if user_id not in self._user_by_id:
            raise UserNotFoundError(user_id)
        return self._user_by_id[user_id]

    @override
    def save_user(self, user: User) -> None:
        self._user_by_id[user.user_id] = user
```

The connection is injected, not built with `self.connection = sqlite3.connect(DB_PATH)`. The injected version can be handed an in-memory database in tests; the other cannot, and forces every test of every method to touch the filesystem. `save_user` commits explicitly because `get_db_connection()` does not.

One contract test runs against both implementations, which is what stops the fake from drifting from the real thing:

```python
@pytest.fixture(params=["sqlite", "in_memory"])
def user_repository(request, sqlite_connection) -> UserRepository:
    if request.param == "sqlite":
        return SqliteUserRepository(sqlite_connection)
    return InMemoryUserRepository()


def test_get_user_raises_not_found_when_user_is_absent(user_repository):
    with pytest.raises(UserNotFoundError):
        user_repository.get_user("missing")


def test_get_user_returns_user_after_save(user_repository):
    user_repository.save_user(ALICE)

    assert user_repository.get_user(ALICE.user_id) == ALICE
```

### Base classes, and why hierarchies stay shallow

A `Base<Role>` class earns its place when several implementations run the same sequence of steps and differ only in some of them. The base runs the sequence in one concrete method, and the varying steps are abstract hooks: the template method pattern. An agent base that always validates input, calls a model, and checks the output against a schema is the typical case in this workspace.

Two levels below the ABC is the limit, because every extra level adds a place where an override can quietly change behavior a reader assumed was fixed. Inheriting only to reuse a helper is the common way hierarchies grow deep. Composing the helper as a collaborator gives the same reuse without the coupling.

## Frontend parity

TypeScript interfaces play the role Pydantic plays in Python, but with a gap worth naming: they are erased at runtime, so a backend response that does not match its declared `interface` produces no error at the boundary — it produces a confusing failure later, wherever the missing field is read.

There is no code generation from the OpenAPI schema, so the shapes in `src/api/client.ts` are kept in sync with the Pydantic models by hand. A backend model change is incomplete until the matching interface is updated. Generating the client from the schema would remove this class of bug and is worth doing if the API grows.

## Enforcement: rules now, lint later

No linter, formatter, or type checker is installed in the scaffold, so review enforces the standards today. When tooling is added, these settings encode the mechanical part:

| Tool | Rules | Enforces |
|---|---|---|
| Ruff | `N` (pep8-naming) | Casing of functions, variables, classes, constants, exceptions (`N818` requires the `Error` suffix) |
| Ruff | `D` with `[tool.ruff.lint.pydocstyle] convention = "google"` | Docstring presence and Google section format |
| Ruff | `ANN` | Type hints on every parameter and return |
| Ruff | `B` (bugbear) | Mutable default arguments, `except` without re-raise context, and similar |
| mypy or pyright, strict | — | ABC contracts and `@override` signatures match |
| ESLint | `@typescript-eslint/naming-convention`, `@typescript-eslint/no-explicit-any` | TypeScript casing and the `any` ban |

What no tool can check: whether the verb matches its lexicon meaning, whether a name says what the thing holds, whether a docstring is *complete*, and whether a subclass honors its contract. Those stay on the review checklist in the skill.

## Sources

- [PEP 8](https://peps.python.org/pep-0008/): naming conventions and casing.
- [PEP 257](https://peps.python.org/pep-0257/): docstring conventions, including the imperative summary line.
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html):
  - §3.8 docstrings (class docstrings describe the instance, exception docstrings describe the error, override rules).
  - §3.16 naming (descriptive names, no type in the name, no abbreviations).
  - §3.18 function length.
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html): identifier casing, no `I` prefix on interfaces, acronyms treated as words, no `_` prefixes.
- [`abc` module](https://docs.python.org/3/library/abc.html) and [`typing.Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol): the instantiation-time vs structural checking tradeoff.
- Published Python coding-standards skills reviewed for coverage, for example python-conventions and python-standards. All converge on PEP 8, type hints, Google docstrings, composition over inheritance, dependency injection, and shallow hierarchies. None mandates ABCs for owned abstractions; that choice is ours, made for the reason given above.
