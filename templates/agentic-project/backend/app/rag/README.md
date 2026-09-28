# `rag/` — document retrieval

Retrieval-augmented generation, minus the generation: this package turns a directory of documents into tenant-scoped, embedded chunks and answers a text query with the most similar passages. An agent that uses the passages is a separate step; nothing here calls a chat model.

**Model judgement vs deterministic code:** an embedding model turns text into vectors (in live mode, OpenAI). Everything else is deterministic: validating the index, checking hashes, splitting, filtering by tenant, and ranking by cosine similarity. **No LLM decides relevance.**

## The pipeline

```text
index-documents                                       search
─────────────────                                     ──────
index.json ─> load_document_index (validate)          query text
   │                                                     │
   ├─> load_document_text (path inside tenant dir,       ├─> embed_query
   │                       SHA-256 must match)           │
   ├─> split_document_text (paragraph chunks ≤ 800)      ├─> VectorQuery(index_version, limit)
   │                                                     │
   ├─> embed_documents (all chunks, batched)             └─> list_nearest_chunks
   │                                                           filter: tenant + index_version
   └─> replace_document_chunks (per document)                  rank: cosine similarity
```

Everything is validated and split **before** the first embedding request, so a bad document fails before any paid call. Every chunk is embedded before the first write, so an embedding failure stores nothing.

## Files

### `contracts.py` — the data shapes

| Contract | Meaning |
|---|---|
| `DocumentEntry` | One entry of `index.json`: `document_id`, `tenant_id`, `document_type` (`policy`, `reference`, or `correspondence`), `title`, `path`, `effective_date`, `version`, `sha256`, and `trust_level: "untrusted_content"` |
| `DocumentChunk` | One passage: a deterministic `chunk_id` (24 hex digits), `tenant_id`, `document_id`, `ordinal`, `text`, and `trust_level` |
| `EmbeddingBatch` | Vectors for a batch of texts, in input order, plus billed tokens if known |
| `EmbeddedChunk` | A chunk, its vector, and the `index_version` it was produced under |
| `VectorQuery` | A query vector, an `index_version`, and a `limit` (1–20) |
| `ScoredChunk` | A retrieved chunk and its cosine similarity |
| `RetrievalQuery` | The caller's search: `text` (≤ 2000 characters) and `limit` (default 5) |
| `IngestionReport` | Documents and chunks indexed, the index version, and tokens |

`trust_level` is always `untrusted_content`: retrieved text is **data, never instructions**. An agent that puts passages into a prompt must present them as quoted content, never as part of the system prompt.

### `embedder.py` — text to vectors

`BaseEmbedder` is the ABC. It implements the shared behavior once:

- `embed_documents(texts)` splits the texts into `profile.max_batch_size` batches and sums the tokens. If any batch lacks a token count, the total becomes `None`, because a partial sum would under-report cost.
- `embed_query(text)` embeds one query.
- `_embed_checked` verifies that each batch has one vector per text, each of exactly `profile.dimensions`. The check lives in the base class so no implementation can return vectors that would silently mis-rank against the stored index.

Subclasses implement only `_embed_texts(texts, kind)`:

- **`HashingEmbedder`** (offline, the fixture profile): hashes lowercase words into signed buckets and normalizes the result to unit length. Similar wording scores higher, but it captures word overlap, not meaning. It verifies the retrieval *wiring*, not retrieval *quality*.
- **`PydanticAIEmbedder`** (live): wraps a Pydantic AI `Embedder` (OpenAI today, built in `bootstrap.py`), requests the profile's dimensions, and maps HTTP errors through `classify_http_status` into a safe `EmbeddingError`.

### `vector_store.py` — tenant-scoped vector storage

`VectorStore` is the ABC:

- `replace_document_chunks(scope, document_id, chunks)` atomically replaces one document's chunks within each index version present in `chunks`. Stale passages from an older revision of the document are removed. Every chunk must belong to `scope` and `document_id`, otherwise `InvalidQueryError`.
- `list_nearest_chunks(scope, query)` returns the best `query.limit` chunks, best first, with ties broken by `chunk_id`.

**The tenant and index-version filter runs before any similarity is computed**, so another tenant's text is never ranked or returned, and cannot leak through scores. Filtering by `index_version` (`provider:model:dimensions`) means vectors from different embedding models are never compared.

Implementations: **`SqlVectorStore`** keeps vectors as JSON arrays in `document_chunks` and ranks them exactly in Python. That is fine for thousands of chunks; replace it with pgvector at scale, behind the same ABC. **`InMemoryVectorStore`** is the test fake, with identical filtering and ordering. `rank_chunks` and `calculate_cosine_similarity` are shared by both.

### `ingestion.py` — indexing a document directory

- `load_document_index(directory)` validates `index.json` and rejects duplicate `document_id`s.
- `load_document_text(directory, entry)` resolves the path and refuses it unless it stays inside `directory/<tenant_id>/`, which prevents path traversal and cross-tenant files. It also refuses files whose bytes do not match `entry.sha256`.
- `split_document_text(entry, text)` splits at blank lines, cuts paragraphs longer than `MAX_CHUNK_CHARACTERS` (800) at word boundaries, then merges consecutive short paragraphs while they fit. Chunk IDs hash the splitter version, document ID, document version, position, and text, so re-indexing unchanged text produces the same IDs.
- `ingest_documents(directory, embedder, store)` runs the whole pipeline and returns an `IngestionReport`.

### `retriever.py` — search

`Retriever(embedder, store).search_chunks(scope, query)` embeds the query and asks the store for that tenant's nearest chunks under the embedder's own `index_version`. The embedder must use the same profile the corpus was indexed with; otherwise the search returns nothing rather than wrong results.

## How it connects

`foundation.py` builds `SqlVectorStore(engine)` and `Retriever(embedder, vector_store)`, with the embedder from `bootstrap.open_embedder`. The CLI's `index-documents` and `search` commands use them. The tenant always comes from the caller (`--tenant`), never from document content or a model.

## How to use

Directory layout (see [`data/README.md`](../../../data/README.md)):

```text
data/raw/documents/2026-09-27/
  index.json
  tenant_alpha/expense-policy.md
  tenant_beta/travel-policy.md
```

```bash
cd backend
.venv/bin/template-cli index-documents --directory ../data/raw/documents/2026-09-27
.venv/bin/template-cli search --tenant tenant_alpha --query "what needs a supporting document"
# Add --live to both for OpenAI embeddings (needs TEMPLATE_OPENAI_API_KEY); index and search with the same profile.
```

Each `index.json` entry's `sha256` is the SHA-256 of the file's bytes, for example from `shasum -a 256 tenant_alpha/expense-policy.md`.

## How to extend

- **Document types:** edit the `document_type` literal in `DocumentEntry`.
- **Another embedding model:** add an `[embedding_profiles.*]` entry in `config/models.toml` and set `default_embedding_profile`. A different `model_id` or `dimensions` gives a new `index_version`, so **reindex** before searching.
- **pgvector:** implement `VectorStore` over a vector column, keeping the tenant and version filter inside the query, and swap it in `foundation.build_foundation`. Run the existing parametrized store tests against it.
- **A different splitter:** change `split_document_text` and bump `SPLITTER_VERSION`, so the new chunk IDs cannot collide with the old ones.

## Tests

`tests/test_rag.py`: embedder batching, shape checks, and error mapping; tenant-isolated ranking and stale-chunk replacement over both stores; stable chunk IDs; rejection of bad index entries before any embedding; and embedding-profile selection.
