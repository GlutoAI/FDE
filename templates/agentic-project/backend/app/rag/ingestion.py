"""Index one document directory: validate its index, split text, embed, and store.

A document directory holds ``index.json`` and one subdirectory per tenant. Every entry's path
must stay inside its own tenant's subdirectory and its bytes must match the
recorded hash; any failure stops ingestion before an embedding request is made.
"""

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.core.context import TenantScope
from app.core.errors import DataImportError
from app.rag.contracts import (
    DocumentChunk,
    DocumentEntry,
    EmbeddedChunk,
    IngestionReport,
)
from app.rag.embedder import BaseEmbedder
from app.rag.vector_store import VectorStore

SPLITTER_VERSION = "paragraph-v1"
MAX_CHUNK_CHARACTERS = 800
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

DOCUMENT_INDEX_ADAPTER = TypeAdapter(list[DocumentEntry])


def load_document_index(directory: Path) -> list[DocumentEntry]:
    """Read and validate ``index.json`` in a document directory.

    Args:
        directory: Document directory, e.g. ``data/raw/documents/<date>/``.

    Returns:
        Every listed document, in index order.

    Raises:
        DataImportError: The index is missing, malformed, or has duplicate document IDs.
    """
    try:
        raw = json.loads((directory / "index.json").read_text(encoding="utf-8"))
        entries = DOCUMENT_INDEX_ADAPTER.validate_python(raw, strict=False)
    except (OSError, ValueError, ValidationError) as error:
        raise DataImportError("invalid_document_index: check index.json") from error
    if len({entry.document_id for entry in entries}) != len(entries):
        raise DataImportError("invalid_document_index: duplicate document_id")
    return entries


def load_document_text(directory: Path, entry: DocumentEntry) -> str:
    """Read one document after checking its location and content hash.

    Args:
        directory: Document directory the entry's path is relative to.
        entry: Index entry naming the file.

    Returns:
        The document text.

    Raises:
        DataImportError: The path leaves the tenant's directory, the file is unreadable,
            or its bytes do not match ``entry.sha256``.
    """
    tenant_directory = (directory / entry.tenant_id).resolve()
    path = (directory / entry.path).resolve()
    if not path.is_relative_to(tenant_directory):
        raise DataImportError(f"invalid_document_path: {entry.document_id}")
    try:
        content = path.read_bytes()
    except OSError as error:
        raise DataImportError(f"unreadable_document: {entry.document_id}") from error
    if hashlib.sha256(content).hexdigest() != entry.sha256:
        raise DataImportError(f"document_hash_mismatch: {entry.document_id}")
    return content.decode("utf-8")


def split_document_text(entry: DocumentEntry, text: str) -> list[DocumentChunk]:
    """Split text at paragraph breaks into chunks of at most ``MAX_CHUNK_CHARACTERS``.

    Consecutive paragraphs share a chunk while they fit; a longer paragraph is cut at word
    boundaries. A single word longer than the limit is kept whole, as its own chunk, rather
    than cut mid-word. Chunk IDs depend on the splitter version, document version, position,
    and text, so re-splitting unchanged text yields the same IDs.

    Args:
        entry: Document the text belongs to.
        text: Full document text.

    Returns:
        Chunks in document order; empty when the text has no content.
    """
    passages = _merge_paragraphs(_split_long_paragraphs(PARAGRAPH_BREAK.split(text)))
    return [
        DocumentChunk(
            chunk_id=_calculate_chunk_id(entry, ordinal, passage),
            tenant_id=entry.tenant_id,
            document_id=entry.document_id,
            ordinal=ordinal,
            text=passage,
        )
        for ordinal, passage in enumerate(passages)
    ]


async def ingest_documents(
    directory: Path, embedder: BaseEmbedder, store: VectorStore
) -> IngestionReport:
    """Validate and split every listed document, embed every chunk, and replace stored chunks.

    Args:
        directory: Document directory holding ``index.json``.
        embedder: Embedding model; its profile sets the index version.
        store: Destination vector storage.

    Returns:
        Documents and chunks indexed, and embedding tokens when known.

    Raises:
        DataImportError: The index or a document is invalid; nothing is embedded.
        EmbeddingError: An embedding request failed; nothing is stored, because every chunk
            is embedded before the first write.
        StorageError: A write failed; documents written before it keep their new chunks,
            and rerunning is safe.
    """
    # Validate and split everything first, so a bad document fails before any paid request.
    documents = [
        (entry, split_document_text(entry, load_document_text(directory, entry)))
        for entry in load_document_index(directory)
    ]
    documents = [(entry, chunks) for entry, chunks in documents if chunks]
    all_chunks = [chunk for _, chunks in documents for chunk in chunks]
    index_version = embedder.profile.index_version
    if not all_chunks:
        return IngestionReport(documents=0, chunks=0, index_version=index_version)
    batch = await embedder.embed_documents([chunk.text for chunk in all_chunks])
    vector_by_chunk_id = dict(
        zip((chunk.chunk_id for chunk in all_chunks), batch.vectors, strict=True)
    )
    for entry, chunks in documents:
        embedded = _build_embedded_chunks(chunks, vector_by_chunk_id, index_version)
        scope = TenantScope(tenant_id=entry.tenant_id)
        await store.replace_document_chunks(scope, entry.document_id, embedded)
    return IngestionReport(
        documents=len(documents),
        chunks=len(all_chunks),
        index_version=index_version,
        input_tokens=batch.input_tokens,
    )


def _build_embedded_chunks(
    chunks: Sequence[DocumentChunk], vector_by_chunk_id: dict[str, list[float]], version: str
) -> list[EmbeddedChunk]:
    """Pair each chunk with its vector under the index version.

    Args:
        chunks: One document's chunks.
        vector_by_chunk_id: Vectors for every chunk in the batch.
        version: Index version the vectors were produced under.

    Returns:
        One embedded chunk per input chunk, in order.
    """
    return [
        EmbeddedChunk(chunk=chunk, vector=vector_by_chunk_id[chunk.chunk_id], index_version=version)
        for chunk in chunks
    ]


def _split_long_paragraphs(paragraphs: Sequence[str]) -> list[str]:
    """Strip paragraphs, drop blank ones, and cut any longer than the limit at word breaks.

    Args:
        paragraphs: Paragraphs as split from the document.

    Returns:
        Pieces of at most ``MAX_CHUNK_CHARACTERS``, except a single overlong word, which is
        kept whole. Whitespace inside a piece is collapsed to single spaces.
    """
    pieces: list[str] = []
    for paragraph in (p.strip() for p in paragraphs):
        current = ""
        for word in paragraph.split():
            if current and len(current) + 1 + len(word) > MAX_CHUNK_CHARACTERS:
                pieces.append(current)
                current = word
            else:
                current = f"{current} {word}" if current else word
        if current:
            pieces.append(current)
    return pieces


def _merge_paragraphs(paragraphs: Sequence[str]) -> list[str]:
    """Join consecutive paragraphs with blank lines while the result fits the limit.

    Args:
        paragraphs: Non-blank pieces from ``_split_long_paragraphs``.

    Returns:
        Passages in order; each is one piece or several separated by a blank line.
    """
    merged: list[str] = []
    for paragraph in paragraphs:
        # + 2 for the blank-line separator ("\n\n").
        if merged and len(merged[-1]) + 2 + len(paragraph) <= MAX_CHUNK_CHARACTERS:
            merged[-1] = f"{merged[-1]}\n\n{paragraph}"
        else:
            merged.append(paragraph)
    return merged


def _calculate_chunk_id(entry: DocumentEntry, ordinal: int, text: str) -> str:
    """Return a stable 24-hex-digit ID for a chunk's position and content.

    Args:
        entry: Document the chunk belongs to; its ID and version are part of the key.
        ordinal: Position of the chunk in the document.
        text: Chunk text.

    Returns:
        The first 24 hex digits of a SHA-256 over the splitter version and those inputs.
    """
    # NUL separators keep ("a", "bc") and ("ab", "c") from hashing the same.
    key = f"{SPLITTER_VERSION}\0{entry.document_id}\0{entry.version}\0{ordinal}\0{text}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]
