"""Verify embedders, vector stores, ingestion, and retrieval, including tenant isolation.

Vector-store tests run against both the in-memory and SQL stores. The OpenAI embedder is
exercised through a mocked HTTP transport, never the network.
"""

import asyncio
import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import override

import httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bootstrap import build_openai_embedder
from app.core.errors import (
    ConfigurationError,
    DataImportError,
    EmbeddingError,
    InvalidQueryError,
)
from app.core.settings import ProjectLocation, load_embedding_profile, load_settings
from app.llm.contracts import EmbeddingProfile
from app.rag.contracts import (
    DocumentChunk,
    EmbeddedChunk,
    EmbeddingBatch,
    RetrievalQuery,
    VectorQuery,
)
from app.rag.embedder import (
    BaseEmbedder,
    HashingEmbedder,
    InputKind,
    calculate_hashed_vector,
)
from app.rag.ingestion import (
    MAX_CHUNK_CHARACTERS,
    ingest_documents,
    load_document_index,
    split_document_text,
)
from app.rag.retriever import Retriever
from app.rag.vector_store import InMemoryVectorStore, SqlVectorStore, VectorStore
from tests.synthetic import (
    ALPHA,
    BETA,
    build_document_entry,
    run_with_engine,
    write_document_import,
)

FIXTURE_PROFILE = EmbeddingProfile(
    provider="fixture", model_id="hashing-test", dimensions=64, timeout_seconds=1, max_batch_size=2
)
OPENAI_PROFILE = EmbeddingProfile(
    provider="openai",
    model_id="text-embedding-3-small",
    dimensions=8,
    timeout_seconds=1,
    max_batch_size=8,
)


class RecordingEmbedder(BaseEmbedder):
    """An embedder that records each batch it receives and returns constant vectors.

    Attributes:
        batches: Texts of every batch, in call order; empty proves nothing was embedded.
    """

    def __init__(self, profile: EmbeddingProfile, *, dimensions: int | None = None) -> None:
        """Use the profile's dimensions, or a wrong length to exercise the shape check."""
        super().__init__(profile)
        self.batches: list[list[str]] = []
        self._dimensions = dimensions or profile.dimensions

    @override
    async def _embed_texts(self, texts: Sequence[str], kind: InputKind) -> EmbeddingBatch:
        self.batches.append(list(texts))
        return EmbeddingBatch(
            model_id="recording", vectors=[[1.0] * self._dimensions for _ in texts], input_tokens=3
        )


def build_embedded_chunk(
    text: str, *, tenant_id: str = "tenant_alpha", document_id: str = "doc-1", version: str = "v1"
) -> EmbeddedChunk:
    """Return a chunk embedded with the 64-dimension hashing vector of its text."""
    chunk = DocumentChunk(
        chunk_id=hashlib.sha256(f"{tenant_id}{document_id}{text}".encode()).hexdigest()[:24],
        tenant_id=tenant_id,
        document_id=document_id,
        ordinal=0,
        text=text,
    )
    return EmbeddedChunk(
        chunk=chunk, vector=calculate_hashed_vector(text, 64), index_version=version
    )


def query_for(text: str, *, version: str = "v1", limit: int = 5) -> VectorQuery:
    """Return a vector query for ``text``, comparable with ``build_embedded_chunk`` vectors."""
    return VectorQuery(vector=calculate_hashed_vector(text, 64), index_version=version, limit=limit)


StoreFactory = Callable[[AsyncEngine], VectorStore]
STORE_FACTORIES: dict[str, StoreFactory] = {
    "memory": lambda engine: InMemoryVectorStore(),
    "sql": SqlVectorStore,
}


@pytest.fixture(params=sorted(STORE_FACTORIES))
def store_factory(request: pytest.FixtureRequest) -> StoreFactory:
    return STORE_FACTORIES[request.param]


def test_hashing_embedder_is_deterministic_unit_length_and_word_sensitive() -> None:
    first = calculate_hashed_vector("Duplicate meal record on the report", 64)
    assert first == calculate_hashed_vector("duplicate MEAL record on the report", 64)
    assert sum(value * value for value in first) == pytest.approx(1.0)
    assert calculate_hashed_vector("", 64) == [0.0] * 64


def test_base_embedder_splits_batches_and_sums_tokens() -> None:
    embedder = RecordingEmbedder(FIXTURE_PROFILE)
    batch = asyncio.run(embedder.embed_documents(["a", "b", "c", "d", "e"]))
    assert [len(texts) for texts in embedder.batches] == [2, 2, 1]
    assert len(batch.vectors) == 5
    assert batch.input_tokens == 9


@pytest.mark.parametrize("texts", [[], ["ok", "  "]])
def test_base_embedder_rejects_empty_or_blank_input(texts: list[str]) -> None:
    with pytest.raises(EmbeddingError, match="invalid_input"):
        asyncio.run(RecordingEmbedder(FIXTURE_PROFILE).embed_documents(texts))


def test_base_embedder_rejects_vectors_of_the_wrong_length() -> None:
    embedder = RecordingEmbedder(FIXTURE_PROFILE, dimensions=3)
    with pytest.raises(EmbeddingError, match="invalid_response"):
        asyncio.run(embedder.embed_query("cash"))


def build_embedding_client(respond: Callable[[httpx.Request], httpx.Response]) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key="test-secret",
        base_url="https://api.openai.com/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    )


def test_openai_embedder_requests_profile_model_and_dimensions() -> None:
    requests: list[dict[str, object]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        data = [
            {"object": "embedding", "index": i, "embedding": [0.25] * 8}
            for i, _ in enumerate(body["input"])
        ]
        usage = {"prompt_tokens": 7, "total_tokens": 7}
        payload = {"object": "list", "data": data, "model": body["model"], "usage": usage}
        return httpx.Response(200, json=payload)

    embedder = build_openai_embedder(OPENAI_PROFILE, build_embedding_client(respond))
    batch = asyncio.run(embedder.embed_documents(["cash", "runway"]))
    assert requests[0]["model"] == "text-embedding-3-small"
    assert requests[0]["dimensions"] == 8
    assert (len(batch.vectors), batch.input_tokens) == (2, 7)


@pytest.mark.parametrize(("status", "code"), [(401, "authentication"), (429, "rate_limit")])
def test_openai_embedder_normalizes_http_errors(status: int, code: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "secret detail", "code": None}})

    embedder = build_openai_embedder(OPENAI_PROFILE, build_embedding_client(respond))
    with pytest.raises(EmbeddingError) as failure:
        asyncio.run(embedder.embed_query("cash"))
    assert str(failure.value).startswith(code)
    assert "secret detail" not in str(failure.value)


def test_openai_embedder_reports_transport_failure_as_network() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    embedder = build_openai_embedder(OPENAI_PROFILE, build_embedding_client(respond))
    with pytest.raises(EmbeddingError, match="network"):
        asyncio.run(embedder.embed_query("cash"))


def test_vector_store_ranks_only_the_tenants_chunks(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        store = store_factory(engine)
        await store.replace_document_chunks(
            ALPHA,
            "doc-1",
            [build_embedded_chunk("missing document for dinner"), build_embedded_chunk("payroll")],
        )
        await store.replace_document_chunks(
            BETA,
            "doc-1",
            [build_embedded_chunk("missing document for dinner", tenant_id="tenant_beta")],
        )
        results = await store.list_nearest_chunks(ALPHA, query_for("missing document"))
        assert [result.chunk.text for result in results] == [
            "missing document for dinner",
            "payroll",
        ]
        assert {result.chunk.tenant_id for result in results} == {"tenant_alpha"}
        assert results[0].score > results[1].score

    run_with_engine(tmp_path, scenario)


def test_vector_store_replacement_removes_stale_chunks_of_that_version(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        store = store_factory(engine)
        await store.replace_document_chunks(ALPHA, "doc-1", [build_embedded_chunk("old text")])
        await store.replace_document_chunks(
            ALPHA, "doc-1", [build_embedded_chunk("old text", version="v2")]
        )
        await store.replace_document_chunks(ALPHA, "doc-1", [build_embedded_chunk("new text")])
        current = await store.list_nearest_chunks(ALPHA, query_for("text"))
        assert [result.chunk.text for result in current] == ["new text"]
        other_version = await store.list_nearest_chunks(ALPHA, query_for("text", version="v2"))
        assert [result.chunk.text for result in other_version] == ["old text"]

    run_with_engine(tmp_path, scenario)


def test_vector_store_rejects_chunks_of_another_tenant(
    tmp_path: Path, store_factory: StoreFactory
) -> None:
    async def scenario(engine: AsyncEngine) -> None:
        foreign = build_embedded_chunk("text", tenant_id="tenant_beta")
        with pytest.raises(InvalidQueryError):
            await store_factory(engine).replace_document_chunks(ALPHA, "doc-1", [foreign])

    run_with_engine(tmp_path, scenario)


def test_split_document_text_bounds_chunks_and_keeps_stable_ids(tmp_path: Path) -> None:
    [entry, _] = load_document_index(write_document_import(tmp_path))
    text = "Intro paragraph.\n\n" + " ".join(["word"] * 400) + "\n\nClosing."
    chunks = split_document_text(entry, text)
    assert all(len(chunk.text) <= MAX_CHUNK_CHARACTERS for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert chunks == split_document_text(entry, text)
    assert split_document_text(entry, "\n\n  \n") == []


def test_ingest_documents_indexes_corpus_and_isolates_tenants(tmp_path: Path) -> None:
    directory = write_document_import(tmp_path)

    async def scenario() -> None:
        store = InMemoryVectorStore()
        embedder = HashingEmbedder(FIXTURE_PROFILE)
        first = await ingest_documents(directory, embedder, store)
        second = await ingest_documents(directory, embedder, store)
        assert first == second
        assert (first.documents, first.chunks) == (2, 2)
        retriever = Retriever(embedder, store)
        results = await retriever.search_chunks(
            ALPHA, RetrievalQuery(text="what needs a supporting document", limit=20)
        )
        assert results and {result.chunk.document_id for result in results} == {"policy-alpha"}

    asyncio.run(scenario())


def build_corpus(tmp_path: Path, *, path: str, content: bytes, recorded: bytes) -> Path:
    """Write a one-document corpus whose index records the hash of ``recorded``."""
    entry = build_document_entry("policy-alpha", "tenant_alpha", path, recorded)
    (tmp_path / "tenant_alpha").mkdir()
    (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / path).write_bytes(content)
    (tmp_path / "index.json").write_text(json.dumps([entry]))
    return tmp_path


@pytest.mark.parametrize(
    ("path", "content", "recorded", "reason"),
    [
        ("tenant_beta/x.md", b"text", b"text", "invalid_document_path"),
        ("tenant_alpha/x.md", b"changed", b"original", "document_hash_mismatch"),
    ],
)
def test_ingest_documents_rejects_bad_entries_before_embedding(
    tmp_path: Path, path: str, content: bytes, recorded: bytes, reason: str
) -> None:
    directory = build_corpus(tmp_path, path=path, content=content, recorded=recorded)
    embedder = RecordingEmbedder(FIXTURE_PROFILE)
    with pytest.raises(DataImportError, match=reason):
        asyncio.run(ingest_documents(directory, embedder, InMemoryVectorStore()))
    assert embedder.batches == []


def test_load_embedding_profile_follows_execution_mode(project_location: ProjectLocation) -> None:
    settings = load_settings(project_location)
    assert load_embedding_profile(project_location, settings).provider == "fixture"
    live = settings.model_copy(update={"model_mode": "live"})
    assert load_embedding_profile(project_location, live).model_id == "text-embedding-3-small"


def test_load_embedding_profile_rejects_missing_default(project_location: ProjectLocation) -> None:
    path = project_location.config_dir / "models.toml"
    path.write_text(path.read_text().replace('default_embedding_profile = "openai_small"\n', ""))
    live = load_settings(project_location).model_copy(update={"model_mode": "live"})
    with pytest.raises(ConfigurationError, match="unknown_embedding_profile"):
        load_embedding_profile(project_location, live)
