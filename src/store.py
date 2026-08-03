from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document

_EMPTY_METADATA_PLACEHOLDER = "__empty__"


def _sanitize_metadata(metadata: dict) -> dict:
    """Chroma rejects empty metadata dicts; substitute a harmless placeholder."""
    return metadata if metadata else {_EMPTY_METADATA_PLACEHOLDER: True}


def _restore_metadata(metadata: dict) -> dict:
    return {} if _EMPTY_METADATA_PLACEHOLDER in metadata else metadata


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
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            client = chromadb.EphemeralClient()
            try:
                client.delete_collection(name=collection_name)
            except Exception:
                pass
            self._collection = client.create_collection(name=collection_name)
            self._use_chroma = True
        except Exception:
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": doc.metadata,
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        query_embedding = self._embedding_fn(query)
        scored = [
            {**record, "score": _dot(query_embedding, record["embedding"])}
            for record in records
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if self._use_chroma:
            storage_ids = []
            for doc in docs:
                storage_ids.append(f"{doc.id}::{self._next_index}")
                self._next_index += 1
            embeddings = [self._embedding_fn(doc.content) for doc in docs]
            metadatas = [
                _sanitize_metadata({**doc.metadata, "doc_id": doc.metadata.get("doc_id", doc.id)})
                for doc in docs
            ]
            self._collection.add(
                ids=storage_ids,
                documents=[doc.content for doc in docs],
                embeddings=embeddings,
                metadatas=metadatas,
            )
        else:
            for doc in docs:
                self._store.append(self._make_record(doc))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if self._use_chroma:
            query_embedding = self._embedding_fn(query)
            result = self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
            records = []
            for i in range(len(result["ids"][0])):
                records.append(
                    {
                        "id": result["ids"][0][i],
                        "content": result["documents"][0][i],
                        "metadata": _restore_metadata(result["metadatas"][0][i]),
                        "score": -result["distances"][0][i],
                    }
                )
            return records
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_chroma:
            return self._collection.count()
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        metadata_filter = metadata_filter or {}
        records = self._store
        if self._use_chroma:
            raw = self._collection.get()
            records = [
                {
                    "id": rid,
                    "content": content,
                    "metadata": _restore_metadata(meta),
                    "embedding": self._embedding_fn(content),
                }
                for rid, content, meta in zip(raw["ids"], raw["documents"], raw["metadatas"])
            ]
        filtered = [
            record
            for record in records
            if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
        ]
        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        def matches(record_id: str, metadata: dict) -> bool:
            return record_id == doc_id or metadata.get("doc_id") == doc_id

        if self._use_chroma:
            raw = self._collection.get()
            ids_to_delete = [
                rid for rid, meta in zip(raw["ids"], raw["metadatas"]) if matches(rid, meta)
            ]
            if not ids_to_delete:
                return False
            self._collection.delete(ids=ids_to_delete)
            return True

        original_len = len(self._store)
        self._store = [
            record for record in self._store if not matches(record["id"], record["metadata"])
        ]
        return len(self._store) != original_len
