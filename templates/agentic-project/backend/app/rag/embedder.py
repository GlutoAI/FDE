"""Turn text into vectors: a shared batching base, an offline hashing embedder, and live models.

Embedding is deterministic code around a model call; which passages are relevant is decided by
vector similarity, not by an LLM.
"""

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Literal, override

from pydantic_ai.embeddings import Embedder
from pydantic_ai.embeddings.settings import EmbeddingSettings
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

from app.core.errors import EmbeddingError
from app.llm.contracts import EmbeddingProfile
from app.llm.runtime import classify_http_status
from app.rag.contracts import EmbeddingBatch

InputKind = Literal["document", "query"]

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class BaseEmbedder(ABC):
    """An embedding model behind one profile, with batching and shape checks shared.

    Attributes:
        profile: Model identity and limits every returned vector must satisfy.
    """

    def __init__(self, profile: EmbeddingProfile) -> None:
        """Store the profile; no client is opened.

        Args:
            profile: Resolved embedding profile.
        """
        self.profile = profile

    async def embed_documents(self, texts: Sequence[str]) -> EmbeddingBatch:
        """Embed passages for storage, splitting them into profile-sized batches.

        Args:
            texts: Non-empty passages, in the order their vectors are returned.

        Returns:
            One vector per text, each of the profile's dimensions.

        Raises:
            EmbeddingError: The input is empty, the request failed, or a vector has the
                wrong count or length.
        """
        if not texts or any(not text.strip() for text in texts):
            raise EmbeddingError("invalid_input: embed at least one non-blank text")
        vectors: list[list[float]] = []
        input_tokens: int | None = 0
        for start in range(0, len(texts), self.profile.max_batch_size):
            batch = await self._embed_checked(texts[start : start + self.profile.max_batch_size])
            vectors.extend(batch.vectors)
            input_tokens = _add_tokens(input_tokens, batch.input_tokens)
        return EmbeddingBatch(
            model_id=self.profile.model_id, vectors=vectors, input_tokens=input_tokens
        )

    async def embed_query(self, text: str) -> list[float]:
        """Embed one search query.

        Args:
            text: Non-blank query text.

        Returns:
            A vector of the profile's dimensions.

        Raises:
            EmbeddingError: The query is blank, the request failed, or the vector is malformed.
        """
        if not text.strip():
            raise EmbeddingError("invalid_input: query text is blank")
        return (await self._embed_checked([text], kind="query")).vectors[0]

    async def _embed_checked(
        self, texts: Sequence[str], *, kind: InputKind = "document"
    ) -> EmbeddingBatch:
        """Embed one batch and verify the vector count and length.

        The shape check lives here, not in each implementation, so no embedder can return
        vectors that would silently mis-rank against the stored index.

        Args:
            texts: One batch, no larger than ``profile.max_batch_size``.
            kind: ``query`` for a search, ``document`` for passages being stored.

        Returns:
            The implementation's batch, now known to hold one vector of the profile's
            dimensions per text.

        Raises:
            EmbeddingError: The request failed or the vectors have the wrong count or length.
        """
        batch = await self._embed_texts(texts, kind)
        is_wrong_length = any(len(v) != self.profile.dimensions for v in batch.vectors)
        if len(batch.vectors) != len(texts) or is_wrong_length:
            raise EmbeddingError("invalid_response: embedding shape does not match the profile")
        return batch

    @abstractmethod
    async def _embed_texts(self, texts: Sequence[str], kind: InputKind) -> EmbeddingBatch:
        """Embed one batch no larger than ``profile.max_batch_size``.

        Args:
            texts: Non-blank texts; the base class has already checked them.
            kind: ``query`` or ``document``; some models embed the two differently.

        Returns:
            One vector per text, in input order, and billed tokens when the provider reports
            them. The base class checks the vector count and length.

        Raises:
            EmbeddingError: Any provider or transport failure, with a safe message.
        """


class HashingEmbedder(BaseEmbedder):
    """An offline embedder hashing words into signed buckets; similar wording scores higher.

    It captures word overlap only, not meaning, so it verifies retrieval wiring rather than
    retrieval quality.
    """

    @override
    async def _embed_texts(self, texts: Sequence[str], kind: InputKind) -> EmbeddingBatch:
        vectors = [calculate_hashed_vector(text, self.profile.dimensions) for text in texts]
        return EmbeddingBatch(model_id=self.profile.model_id, vectors=vectors)


class PydanticAIEmbedder(BaseEmbedder):
    """A hosted embedding model reached through a Pydantic AI ``Embedder``."""

    def __init__(self, profile: EmbeddingProfile, embedder: Embedder) -> None:
        """Bind a configured Pydantic AI embedder to its profile.

        Args:
            profile: Model identity and limits.
            embedder: Pydantic AI embedder whose client the composition root owns.
        """
        super().__init__(profile)
        self._embedder = embedder

    @override
    async def _embed_texts(self, texts: Sequence[str], kind: InputKind) -> EmbeddingBatch:
        settings = EmbeddingSettings(dimensions=self.profile.dimensions)
        try:
            if kind == "query":
                result = await self._embedder.embed_query(list(texts), settings=settings)
            else:
                result = await self._embedder.embed_documents(list(texts), settings=settings)
        except ModelHTTPError as error:
            code = classify_http_status(error.status_code, error.body)
            raise EmbeddingError(f"{code}: embedding provider rejected the request") from error
        except (ModelAPIError, TimeoutError) as error:
            raise EmbeddingError("network: embedding request failed") from error
        return EmbeddingBatch(
            model_id=result.model_name,
            vectors=[list(vector) for vector in result.embeddings],
            input_tokens=result.usage.input_tokens or None,
        )


def calculate_hashed_vector(text: str, dimensions: int) -> list[float]:
    """Return a unit-length vector of hashed lowercase word counts.

    Args:
        text: Text to embed.
        dimensions: Vector length.

    Returns:
        The normalized vector; all zeros when the text has no words.
    """
    vector = [0.0] * dimensions
    for token in TOKEN_PATTERN.findall(text.lower()):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        # A hashed sign lets colliding words cancel out on average instead of piling up.
        vector[bucket] += 1.0 if digest[4] % 2 == 0 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _add_tokens(total: int | None, batch_tokens: int | None) -> int | None:
    """Sum token counts, becoming unknown once any batch lacks a count.

    Args:
        total: Running total, or None once unknown.
        batch_tokens: This batch's count, or None when the provider did not report it.

    Returns:
        The new total, or None; a partial sum would under-report cost.
    """
    return None if total is None or batch_tokens is None else total + batch_tokens
