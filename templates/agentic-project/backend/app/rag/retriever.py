"""Answer a tenant's text search by embedding the query and ranking that tenant's chunks."""

from app.core.context import TenantScope
from app.rag.contracts import RetrievalQuery, ScoredChunk, VectorQuery
from app.rag.embedder import BaseEmbedder
from app.rag.vector_store import VectorStore


class Retriever:
    """Semantic search over one embedding profile's index.

    Not an ABC: it has one implementation, and tests substitute the embedder and store.
    Ranking is deterministic vector similarity; no model decides relevance here.
    """

    def __init__(self, embedder: BaseEmbedder, store: VectorStore) -> None:
        """Compose the query embedder and the store it was indexed into.

        Args:
            embedder: Must use the same profile the corpus was ingested with.
            store: Vector storage to search.
        """
        self._embedder = embedder
        self._store = store

    async def search_chunks(self, scope: TenantScope, query: RetrievalQuery) -> list[ScoredChunk]:
        """Return the tenant's passages most similar to the query text.

        Args:
            scope: Tenant the caller acts for; it comes from the backend, never the model.
            query: Search text and result limit.

        Returns:
            Up to ``query.limit`` passages, best first; empty when nothing is indexed under the
            embedder's index version. Passage text is untrusted content.

        Raises:
            EmbeddingError: The query could not be embedded.
            StorageError: The search failed.
        """
        vector = await self._embedder.embed_query(query.text)
        vector_query = VectorQuery(
            vector=vector,
            index_version=self._embedder.profile.index_version,
            limit=query.limit,
        )
        return await self._store.list_nearest_chunks(scope, vector_query)
