from __future__ import annotations

import re
import uuid
from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._client = None
        self._collection = None
        self._next_index = 0

        try:
            import chromadb

            # Each EmbeddingStore instance is isolated.  A unique backend name
            # prevents Chroma's process-wide ephemeral client from leaking data
            # between stores that happen to use the same logical name.
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "-", collection_name).strip(".-")
            safe_name = safe_name or "documents"
            backend_name = f"{safe_name[:40]}-{uuid.uuid4().hex[:12]}"
            self._client = chromadb.EphemeralClient()
            self._collection = self._client.get_or_create_collection(
                name=backend_name,
                metadata={"hnsw:space": "ip"},
            )
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._client = None
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        metadata = dict(doc.metadata)
        metadata.setdefault("doc_id", doc.id)
        embed_document = getattr(self._embedding_fn, "embed_document", self._embedding_fn)
        embedding = [float(value) for value in embed_document(doc.content)]
        storage_id = f"{doc.id}::stored_{self._next_index}"
        self._next_index += 1
        return {
            "id": doc.id,
            "storage_id": storage_id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": embedding,
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0 or not records:
            return []

        embed_query = getattr(self._embedding_fn, "embed_query", self._embedding_fn)
        query_embedding = [float(value) for value in embed_query(query)]
        ranked = sorted(
            records,
            key=lambda record: _dot(query_embedding, record["embedding"]),
            reverse=True,
        )[:top_k]
        return [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": dict(record["metadata"]),
                "score": float(_dot(query_embedding, record["embedding"])),
            }
            for record in ranked
        ]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        records = [self._make_record(doc) for doc in docs]
        self._store.extend(records)

        if self._use_chroma and self._collection is not None:
            try:
                # Chroma accepts scalar metadata only.  Keep the original
                # metadata in the in-memory source of truth used by searches.
                chroma_metadata = []
                for record in records:
                    normalized = {}
                    for key, value in record["metadata"].items():
                        if value is None:
                            continue
                        normalized[str(key)] = (
                            value if isinstance(value, (str, int, float, bool)) else str(value)
                        )
                    chroma_metadata.append(normalized)

                self._collection.add(
                    ids=[record["storage_id"] for record in records],
                    documents=[record["content"] for record in records],
                    embeddings=[record["embedding"] for record in records],
                    metadatas=chroma_metadata,
                )
            except Exception:
                # Required lab behavior remains available without Chroma.
                self._use_chroma = False

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered = [
            record
            for record in self._store
            if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        removed = [
            record for record in self._store if record["metadata"].get("doc_id") == doc_id
        ]
        if not removed:
            return False

        removed_ids = [record["storage_id"] for record in removed]
        self._store = [
            record for record in self._store if record["metadata"].get("doc_id") != doc_id
        ]

        if self._use_chroma and self._collection is not None:
            try:
                self._collection.delete(ids=removed_ids)
            except Exception:
                self._use_chroma = False
        return True
