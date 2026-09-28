---
name: coding-standards
description: Coding standards for all application code in this workspace (backend/, frontend/, and each project's src/) covering naming (verb-first function names, noun variables and classes, boolean prefixes, Python and TypeScript casing), complete docstrings for modules, classes, methods and exceptions, single-responsibility functions and size limits, Pydantic input/output models, object-oriented design with abc.ABC base classes for every abstraction we own, SOLID, composition, dependency injection, encapsulation, exception hierarchies, and unit tests. Use when writing, reviewing, or refactoring Python or TypeScript application code, and when adding classes, endpoints, services, repositories, providers, or components. Not for standalone data scripts such as cashflow-copilot/scripts/.
---

# Coding Standards

These are requirements, not suggestions. Code that violates them is refactored before it counts as done.

## Scope

- **In scope:** all application code in the workspace, including `backend/`, `frontend/`, and each project's `backend/app/` and `frontend/` (for example `cashflow-copilot/backend/app/`).
- **Exempt:** standalone data scripts such as `cashflow-copilot/scripts/generate_data.py` and `validate_data.py`: standard library only, Python 3.9+, plain dicts, deterministic output. No skill generates these at initialization.
- **Where a project differs:** a project's own plan decides paths, database, and test layout. The rules on naming, docstrings, functions, and OOP here apply unchanged. [Scaffold traps](#scaffold-traps-backend-and-frontend-only) applies only to `backend/` and `frontend/`.

## Non-negotiables

Every function, method, and class you write or touch must satisfy all of these:

- [ ] Its name follows [Naming](#naming): functions and methods start with a verb, variables and classes are nouns, booleans read as yes/no questions
- [ ] It has a complete docstring (see [Docstrings](#docstrings-complete-descriptions)); modules have one too
- [ ] It does exactly one thing: the body is 30 lines or fewer, nesting is 3 levels or fewer, and it takes 4 positional parameters or fewer
- [ ] It takes a Pydantic model in and returns a Pydantic model out when it crosses a module boundary
- [ ] Every parameter and return value has a type hint
- [ ] Each abstraction we own is an `abc.ABC`, and concrete classes and test fakes inherit it
- [ ] Collaborators are injected through `__init__`, and `__init__` performs no I/O
- [ ] It has unit tests covering the happy path, edge cases, and failure modes

## Naming

A reader should know what a name does or holds without opening its definition. Names are descriptive, spelled out, and consistent across the codebase.

### Casing

| Identifier | Python | TypeScript |
|---|---|---|
| Module / file | `invoice_repository.py` | `invoiceRepository.ts`; components `InvoiceTable.tsx` |
| Function, method | `calculate_runway` | `calculateRunway` |
| Variable, parameter, attribute | `amount_cents` | `amountCents` |
| Class, ABC, exception, type, interface | `InvoiceRepository` | `InvoiceRepository` |
| Constant | `MAX_RETRY_ATTEMPTS` | `MAX_RETRY_ATTEMPTS` |
| Internal (not part of the public API) | `_parse_row` | the `private` keyword; no `_` prefix |
| Type parameter | `T`, `InvoiceT` | `T`, `TInvoice` |

Acronyms: Python classes keep them upper case (`HTTPClient`, `MCPServer`). TypeScript treats them as words (`HttpClient`, `customerId`, `loadHttpUrl`).

### Functions and methods: verb first

Every function and method name starts with a verb that says what it does, followed by what it acts on: `<verb>_<object>[_<qualifier>]`. Use one verb per meaning across the whole codebase:

| Verb | Meaning | Returns / raises |
|---|---|---|
| `get_` | Return one existing thing by its key | Raises `<Thing>NotFoundError` if absent |
| `find_` | Search for something that may not exist | `None` or an empty collection |
| `list_` | Return a collection matching criteria | A possibly empty list |
| `load_` / `save_` | Read from / write to local storage or files | The loaded model / `None` |
| `fetch_` | Retrieve over the network from a service we don't own | The response model |
| `create_` / `update_` / `delete_` | Persist a change | The created or updated model |
| `calculate_` | Pure derivation from inputs, no I/O | The computed value |
| `build_` | Assemble an object in memory, no I/O | The built model |
| `parse_` / `format_` | Text or bytes to structure / structure to text | The parsed model / `str` |
| `validate_` | Check invariants | `None`; raises on violation |
| `is_` / `has_` / `can_` / `should_` | Answer a yes/no question, no side effects | `bool` |
| `send_` / `publish_` | Cause an external side effect | A receipt or `None` |
| `ensure_` | Make a state true idempotently | `None` |
| `to_` / `from_` | Convert (`to_dict`, classmethod `from_row`) | The converted value |
| `handle_` (TS: `handleX`) | React to an event | Depends on the event |

- **Name the object and qualifier:** `list_overdue_invoices`, not `list_invoices2` or `get_data`.
- **Banned names on their own:** `process`, `handle`, `do`, `run`, `execute`, `manage`, `data`, `info`, `util`, `helper`, `temp`, `obj`, `thing`. They are allowed only with an object, as in `run_evaluation_suite`.
- **Exceptions to verb-first:**
  - `@property` names are nouns (`invoice.total_cents`), because they read as attributes.
  - Dunder methods keep their required names.
  - pytest fixtures are nouns for what they provide (`user_repository`).
  - Test functions follow [Unit tests](#unit-tests).
- **Route handlers are functions too:** `get_invoice`, `create_reminder_draft`, `check_health`.

### Variables and attributes: nouns

- **Name what it holds, with the unit** when it is a quantity: `amount_cents`, `timeout_seconds`, `created_at` (a datetime), `due_date` (a date).
- **Booleans are questions:** `is_overdue`, `has_approval`, `can_send`, `should_retry`. Never negate them (`is_not_valid`); invert at the call site instead.
- **Collections are plural:** `invoices`. Mappings are named `<value>_by_<key>`: `invoice_by_id`, `balance_cents_by_account`.
- **No type in the name:** `invoice_list` and `id_to_name_dict` are out. The type hint already says it.
- **No abbreviations or deleted letters:** `customer_id`, not `cstmr_id` or `cid`. Only universally known forms are allowed (`id`, `url`, `http`, `db`, `api`, `llm`).
- **Single letters** only for loop counters, comprehension variables in scopes of 10 lines or fewer, `e` for a caught exception, and `f` for a file handle.
- **Don't shadow builtins:** `invoice_id`, not `id`; `record_type`, not `type`.
- **Constants** state their unit or meaning: `DEFAULT_TIMEOUT_SECONDS`, `MAX_TOOL_CALLS_PER_TURN`.

### Classes: nouns

- **A class name is a noun** for what one instance *is*: `InvoiceRepository`, `CashflowForecast`, `ReminderDraft`. Avoid `Manager`, `Handler`, `Processor`, and `Helper` unless the domain really uses that word.
- **An abstraction ABC takes the role name:** `InvoiceRepository`, `ModelProvider`, `Sender`, `Clock`.
- **Implementations prefix how they do it:**
  - `SqliteInvoiceRepository`, `AnthropicModelProvider`, `SystemClock`.
  - Test fakes: `InMemoryInvoiceRepository`, `FrozenClock`, `RecordingSender`.
- **A base class with shared implementation** is `Base<Role>`, for example `BaseAgent` or `BaseTool`. There are no `I`, `Abstract`, or `Interface` prefixes, in either language.
- **Exceptions end in `Error`:** `InvoiceNotFoundError`, `ApprovalRequiredError`.
- **Pydantic models:** use `<Action>Request` / `<Action>Response` at routes and plain nouns for internal value objects.

## Docstrings: complete descriptions

Every module, class, method, function, and exception gets a Google-style docstring, private ones included. A docstring is complete when a caller can use the thing correctly without reading its body.

- **Module:** one line saying what the module provides, then what it depends on or must not depend on, where that matters.
- **Class:**
  - A summary of what an instance *represents* ("A repository of invoices stored in SQLite."), not "Class that…".
  - Then an `Attributes:` section for every public attribute.
  - Constructor parameters go in the class docstring or in `__init__`'s docstring, not both.
- **Function / method:**
  - An imperative summary line ("Return the invoice with the given ID.").
  - Then, as applicable, `Args:` (every parameter, with its meaning, units, and constraints), `Returns:` (what, including when it is `None` or empty), `Yields:`, and `Raises:` (every exception raised deliberately, with its condition).
  - State side effects explicitly: writes, commits, sends, network calls.
- **Exception:** describe what the error *represents*, not where it is raised.
- **Abstract method:** the docstring *is* the contract. State what every implementation must return, raise, and guarantee.
- **Override:**
  - Decorate with `@typing.override` (Python 3.12+).
  - Leave the docstring out when behavior matches the base contract; the base docstring applies.
  - Write one only when the override refines the contract, for example a narrower exception or an extra side effect.
- **Pydantic field:** `Field(description=...)` on every field. This is the field's documentation, and it flows into OpenAPI.
- **Test function / fixture:** the behavior-stating name is the description. Add a docstring only when the setup or the reason for the case is not obvious from the name.

```python
"""Invoice persistence backed by SQLite."""


class SqliteInvoiceRepository(InvoiceRepository):
    """A repository of invoices stored in a SQLite database.

    Attributes:
        connection: Open connection used for every query; the caller owns its lifecycle.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    @override
    def get_invoice(self, invoice_id: str) -> Invoice:
        row = self.connection.execute(SELECT_INVOICE_SQL, (invoice_id,)).fetchone()
        if row is None:
            raise InvoiceNotFoundError(invoice_id)
        return Invoice.from_row(row)


class InvoiceNotFoundError(LedgerError, LookupError):
    """No invoice exists with the requested ID.

    Attributes:
        invoice_id: The ID that was looked up.
    """

    def __init__(self, invoice_id: str) -> None:
        super().__init__(f"No invoice with ID {invoice_id}")
        self.invoice_id = invoice_id
```

Comments inside a body explain *why* (a constraint, a workaround, a business rule), never *what* the next line does. TypeScript uses TSDoc (`/** … */` with `@param`, `@returns`, `@throws`) on every exported function, class, interface, hook, and component.

## Pydantic contracts

Define an explicit input model and output model for every function that crosses a module boundary. Do not pass loose dicts, tuples, or long primitive argument lists between modules — an unvalidated dict crossing a boundary is a runtime error waiting to happen.

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthCheckResult(BaseModel):
    """Outcome of a database connectivity probe."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "error"] = Field(description="Overall probe outcome")
    db: Literal["connected", "disconnected"] = Field(description="Database reachability")
    detail: str | None = Field(default=None, description="Error text when status is error")
```

- **Where models live:** next to the code they serve, in `app/schemas/<domain>.py` in the scaffold, or beside their subpackage in a project's `backend/app/` (for example `app/rag/contracts.py`).
- **Value objects are frozen** (`ConfigDict(frozen=True)`), so they can be shared without defensive copies.
- **Constraints go in `Field`:** use it for constraints and descriptions rather than validating by hand.
- **Boundary exceptions: constructors/factories may accept or return typed collaborators; lifecycle and validation methods may return `None`; predicates and clocks may return typed scalars. Pydantic models validate data payloads, not dependency containers.
- **Private helper exemption:**** module-private helpers prefixed with `_`, used only within their own file, may take and return primitives. Everything else gets models.
- **FastAPI routes:** declare `response_model` on every route so responses are validated and documented, not just type-hinted.

## Function design

One responsibility per function. If you need "and" to describe what it does, split it. The usual split is fetch, transform, persist — keep those separate so each can be tested without the others.

Keep bodies to 30 lines. A longer function is a signal that a named sub-step is hiding inside it; extract that step. Keep nesting to 3 levels — use early returns and guard clauses instead of `else` branches.

Four positional parameters is the maximum. Past that, the arguments are a concept that deserves its own model. Make flags and optional settings keyword-only (`def list_invoices(*, is_overdue: bool = False)`). A boolean flag that switches between two behaviors means two functions.

Separate pure logic from I/O. A function that computes should not also open a database connection, because that makes it untestable without one.

Type-hint every parameter and return. Use `X | None` rather than `Optional[X]` and built-in generics (`list[Invoice]`). `Any` needs a comment saying why no real type exists. Never use mutable default arguments.

## Object-oriented design

### When to write a class

Use a class when you have state plus behavior over that state, or when you need a substitutable implementation of an abstraction. A module-level function is better when you have neither. A class with one public method and no state is a function.

### Abstract base classes for every abstraction we own

An abstraction is anything a caller should not care about the implementation of: repositories, services with swappable implementations, model and tool providers, senders, clocks, ID generators. Each one we own is an `abc.ABC`.

```python
from abc import ABC, abstractmethod


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
        self.frozen_at = frozen_at

    @override
    def get_current_time(self) -> datetime:
        return self.frozen_at
```

1. **Every contract method** is `@abstractmethod`, fully type-hinted, with a docstring that states the contract.
2. **Concrete classes inherit the ABC explicitly** and mark each implementation `@override`. A class missing a method then fails at instantiation with `TypeError`, not at the first call in production.
3. **Test fakes inherit the same ABC.** A fake that drifts from the contract breaks immediately.
4. **Callers type-hint the ABC**, never a concrete class. Only the composition root names concrete classes: FastAPI dependencies in the scaffold, `bootstrap`/`main` in a project.
5. **Interface ABCs hold no state and no `__init__`.** Shared state or logic belongs in a `Base<Role>` class (below).
6. **`typing.Protocol` is only for types we don't own** (describing a third-party object we accept) **and for callback signatures.** Do not use it for our own abstractions.
7. **Do not create an ABC speculatively.** One implementation and no fake means no ABC yet. Add it when the second implementation or the fake arrives.

### Base classes that share implementation

When several implementations share an algorithm and differ in steps, write a `Base<Role>(ABC)`:
- A concrete public *template method* runs the fixed sequence.
- `@abstractmethod` hooks cover the varying steps.
- Hooks that callers must not invoke directly are `_protected`.

Subclasses that define `__init__` call `super().__init__()`.

Keep hierarchies shallow: at most two levels below the ABC. Never inherit to reuse a helper — extract the helper into a collaborator and compose it.

### SOLID, applied

- **Single responsibility:** a class has one reason to change. If its fields split into groups used by different methods, it is two classes.
- **Open/closed:** add a behavior by adding a new implementation of an ABC, not an `if kind == "..."` branch in existing code.
- **Liskov substitution:** a subclass honors its base contract. It accepts everything the base accepts, returns what the base promises, and raises only the base's exceptions or their subclasses. It never raises `NotImplementedError` for an inherited method.
- **Interface segregation:** keep ABCs small and role-shaped (`InvoiceReader` and `InvoiceWriter` rather than one wide `InvoiceStore`). A client depends only on the methods it calls.
- **Dependency inversion:** high-level services receive their collaborators as ABC-typed `__init__` parameters. They never construct them.

### Encapsulation and construction

- **`__init__` assigns attributes and nothing else.** No I/O, no queries, no heavy computation — constructing an object must not have side effects. If construction needs I/O, write a `from_<source>` classmethod or a factory function.
- **Internal attributes and methods use one leading underscore.** No `__double` name mangling.
- **No trivial getters and setters.** Expose a public attribute, use `@property` for cheap derived values, and use a verb method (`calculate_`, `fetch_`) for anything costly or effectful.
- **No mutable class-level state and no module-level singletons** holding connections or clients. Pass them in.
- **Prefer composition over inheritance.** Inherit only for a genuine "is-a" relationship with an ABC or `Base<Role>` you own.

### Exception classes

Each package defines one base exception (`<Package>Error(Exception)`). Specific errors subclass it, or the matching built-in (`InvoiceNotFoundError(<Package>Error, LookupError)`). Carry the identifying data as attributes.

Raise the most specific exception and catch only what you can handle. No bare `except:` and no `except Exception` outside the top-level boundary that turns errors into responses. Re-raise with `raise … from error` to keep the cause.

## Unit tests

Every new function ships with tests in the same change. Untested code is incomplete.

Mirror the source layout under the project's `tests/` (`backend/tests/` in the scaffold). Use pytest, name files `test_<module>.py`, and name each test `test_<unit>_<behavior>[_when_<condition>]`: `test_check_health_returns_503_when_database_is_unreachable`.

Structure each test as arrange, act, assert, with one behavior per test. Several assertions about the same behavior are fine; testing two behaviors in one test is not.

Cover three cases for every function: the happy path, boundaries and edge cases, and each failure mode including the exceptions in the docstring.

Default unit and contract tests must not touch the network or the real database. Explicit integration tests and separately invoked, user-authorized connectivity smoke commands may exercise real boundaries; label them clearly and keep them outside the default suite. Use `tmp_path` for SQLite fixtures and inject fakes through the constructor. A test suite that depends on ambient state fails for reasons unrelated to the code.

When an ABC has more than one implementation, write one parametrized *contract test* and run it against every implementation, fake included. That is what keeps the fake honest.

## TypeScript

The same principles apply on the frontend, with TypeScript types filling the role Pydantic plays in Python.

- **API types:**
  - Export an explicit `interface` for every API request and response in the API client (`src/api/client.ts` in the scaffold).
  - Keep those shapes in sync with the backend Pydantic models by hand. There is no code generation, so a backend change means a matching frontend edit.
- **Contracts:** use `interface` for contracts and shapes, with no `I` prefix. Classes implementing a contract declare `implements` explicitly. Use `abstract class` only when implementation is shared, named `Base<Role>`.
- **Naming:**
  - Components are `PascalCase` nouns (`InvoiceTable`).
  - Hooks are `useX` (`useOverdueInvoices`).
  - Event handlers are `handleX`, and the props that receive them are `onX`.
  - Booleans follow the same `is`/`has`/`can`/`should` rule.
- **No `any`:** prefer `unknown` plus narrowing.
- **Components stay presentational** where possible, with data fetching lifted into hooks or the API client.

## Scaffold traps (`backend/` and `frontend/` only)

`get_db_connection()` in `app/database.py` does **not** commit. Any write needs an explicit `conn.commit()`.

Backend route paths must not include an `/api` prefix — Vite strips it when proxying. See [architecture.md](../../../wiki/reference/architecture.md).

`init_db()` creates no tables. New schema goes there.

## Enforcement

Check each project’s actual tooling rather than assuming repository-wide installation. Cashflow’s initialization foundation configures Ruff and strict mypy. Adopt these rules in new projects; reviewers still check semantics:
- **Python — Ruff:** `N` (pep8-naming), `D` with `convention = "google"` (docstrings), `ANN` (annotations), and `B` (bugbear, which catches mutable defaults).
- **Python — type checker:** mypy or pyright in strict mode.
- **TypeScript:** ESLint `@typescript-eslint/naming-convention` and `@typescript-eslint/no-explicit-any`.

No linter can check that a function name starts with the *right* verb or that a docstring is complete. Those stay review items.

## Review checklist

- [ ] Every function name starts with a verb from the lexicon, used with its lexicon meaning
- [ ] No banned, abbreviated, type-suffixed, or single-letter names outside the allowed cases
- [ ] Every module, class, method, function, and exception has a complete docstring; abstract methods state the contract
- [ ] Every owned abstraction is an ABC; implementations and fakes inherit it and use `@override`; callers type-hint the ABC
- [ ] `Protocol` appears only for third-party types or callbacks
- [ ] No I/O in `__init__`; collaborators injected; hierarchy at most two levels below the ABC
- [ ] Specific exceptions, raised `from` their cause, all descending from the package base error
- [ ] Tests cover the happy path, edge cases, and failures; a contract test covers every implementation of each ABC

## Detailed reference

Full rationale, worked examples, and the test-layout conventions are in [wiki/reference/coding-standards.md](../../../wiki/reference/coding-standards.md).
