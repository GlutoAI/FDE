# `memory/` — conversation history and approved preferences

Two kinds of agent memory, both tenant-scoped:

- **Short-term:** the message history of a conversation thread, so a later turn can continue an earlier one.
- **Long-term:** preferences a user has explicitly approved, such as "summaries in bullet points", valid until they expire or are revoked.

**Memory is context, not a source of truth.** It shapes style and continuity. It never overrides record amounts, record status, permissions, or approval requirements; those are always re-read from their sources. An old message that says "the balance is $40" is not evidence of today's balance.

## Files

### `conversation.py` — message history per thread

`ConversationStore` is the ABC:

| Method | Behavior |
|---|---|
| `save_messages(scope, thread_id, messages)` | Appends messages. The first save creates the thread and makes `scope`'s tenant its owner |
| `load_messages(scope, thread_id, *, limit)` | The most recent `limit` messages (1 to `MAX_HISTORY_MESSAGES` = 200), oldest first; empty for an unknown thread |

Both raise `AccessDeniedError` when another tenant owns the thread (`validate_thread_owner`). Messages are stored in **Pydantic AI's own format** (`ModelMessage`, serialized with `ModelMessagesTypeAdapter`), so what you load can be passed straight back to an agent as `message_history`.

- **`SqlConversationStore(engine)`** writes to `conversation_threads` (the owner) and `conversation_messages` (one JSON row per message, numbered by `sequence`). Ownership check, sequence lookup, and inserts happen in one transaction. Loading reads newest first with `LIMIT`, then reverses, so the window is the most recent one, in chronological order.
- **`InMemoryConversationStore`** is the test fake.

**Caveat:** a bounded window can start with a tool result whose tool call was cut off. Before passing history to a model, start the window at a user request.

### `preferences.py` — approved long-term preferences

- **`MemoryPreference`** is a `TenantRecord` keyed by `preference_id`. It has an optional `record_id` (`None` means tenant-wide), `key`, `value` (untrusted text, at most 500 characters), `approved_by`, `status` (`approved`, `pending`, or `revoked`), `source`, `created_at`, and `expires_at`.
  - `is_active_at(now)` is true only when the preference is `approved`, has started (`created_at <= now`), and has not expired (`now < expires_at`, or `expires_at` is `None`).
- **`PreferenceMemory(repository, clock)`**, where `list_active_preferences(scope, *, record_id=None)` returns the tenant-wide preferences plus those for `record_id`, **active now** according to the injected `Clock`. It considers only the tenant's first `MAX_LIST_LIMIT` stored preferences.
- **`load_preference_records(path)`** reads and validates a `preferences.json` array; any invalid entry raises `DataImportError` and nothing is loaded.

Preferences are stored through the generic `SqlRecordRepository` in `memory_preferences`. Its composite foreign key means a preference can only reference a record of the **same** tenant.

`PreferenceMemory` is not an ABC: it has one implementation, and tests substitute its collaborators (an `InMemoryRecordRepository` and a `FrozenClock`) instead.

## How it connects

`foundation.py` builds `SqlConversationStore(engine)`, and builds `PreferenceMemory` over `SqlRecordRepository(engine, memory_preferences, MemoryPreference)` with the foundation's clock. `import_seed_data` loads `preferences.json` when it sits beside the CSVs.

## How to use

Continue a conversation with an agent's runtime:

```python
from pydantic_ai import Agent

from app.core.context import TenantScope
from app.memory.conversation import ConversationStore


async def continue_thread(
    runtime: Agent[None, str], store: ConversationStore, scope: TenantScope, thread_id: str
) -> str:
    history = await store.load_messages(scope, thread_id, limit=50)
    result = await runtime.run("And what about next month?", message_history=history)
    await store.save_messages(scope, thread_id, result.new_messages())
    return result.output
```

Read the preferences that apply now:

```python
from app.core.context import TenantScope
from app.foundation import Foundation


async def list_style_hints(foundation: Foundation, record_id: str) -> list[str]:
    scope = TenantScope(tenant_id="tenant_alpha")
    preferences = await foundation.preferences.list_active_preferences(scope, record_id=record_id)
    return [f"{preference.key}: {preference.value}" for preference in preferences]
```

Preference values are untrusted text written by users. Present them to a model as data, for example in the request, not as system instructions.

## How to extend

- **Preferences about a different record type:** change `record_id` and the foreign key in `db/tables.py` to point at the new table.
- **Capturing preferences at runtime:** add a write path that creates `status="pending"` preferences, and a separate, human approval step that sets `approved`. An agent must never approve its own memory.

## Tests

`tests/test_memory.py`: history windows and order, cross-tenant denial for reads and writes, history limits, a SQL history feeding a later agent run, preference activity and expiry with a frozen clock, and the cross-tenant foreign key.
