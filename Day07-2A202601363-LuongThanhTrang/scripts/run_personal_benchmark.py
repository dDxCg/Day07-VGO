#!/usr/bin/env python3
"""Run the five provisional Lab 7 retrieval queries on the VNU corpus."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingest import build_knowledge_base
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import LocalEmbedder, OpenAIEmbedder, _mock_embed


DEFAULT_DATA_DIR = Path("data/vnu_university")
DEFAULT_QUERIES = DEFAULT_DATA_DIR / "benchmark_queries.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--provider", choices=("mock", "local", "openai"), default=None)
    parser.add_argument("--chunker", choices=("fixed", "sentence", "recursive"), default="recursive")
    parser.add_argument("--chunk-size", type=int, default=700)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", type=Path, help="Optional JSON file for reproducible results")
    return parser.parse_args()


def select_embedder(provider: str) -> tuple[Callable[[str], list[float]], str]:
    if provider == "local":
        embedder = LocalEmbedder()
        return embedder, embedder._backend_name
    if provider == "openai":
        embedder = OpenAIEmbedder()
        return embedder, embedder._backend_name
    return _mock_embed, _mock_embed._backend_name


def select_chunker(name: str, chunk_size: int):
    if chunk_size <= 0:
        raise ValueError("--chunk-size must be greater than 0")
    if name == "fixed":
        overlap = min(100, max(0, chunk_size // 7))
        return FixedSizeChunker(chunk_size=chunk_size, overlap=overlap)
    if name == "sentence":
        return SentenceChunker(max_sentences_per_chunk=max(1, chunk_size // 100))
    return RecursiveChunker(chunk_size=chunk_size)


def load_queries(path: Path) -> list[dict[str, Any]]:
    queries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(queries, list) or len(queries) != 5:
        raise ValueError("Benchmark file must contain exactly five queries.")
    required = {"id", "query", "gold_answer", "expected_doc_id", "metadata_filter"}
    for query in queries:
        if not isinstance(query, dict) or not required.issubset(query):
            raise ValueError(f"Invalid benchmark query: {query!r}")
        if not isinstance(query["metadata_filter"], dict):
            raise ValueError(f"metadata_filter must be an object: {query['id']}")
    return queries


def main() -> int:
    args = parse_args()
    load_dotenv(override=False)
    provider = args.provider or os.getenv("EMBEDDING_PROVIDER", "mock").strip().lower()
    if provider not in {"mock", "local", "openai"}:
        raise ValueError("EMBEDDING_PROVIDER must be mock, local, or openai")
    if not args.data_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {args.data_dir}")
    if not args.queries.is_file():
        raise FileNotFoundError(f"Benchmark query file not found: {args.queries}")

    embedder, backend = select_embedder(provider)
    chunker = select_chunker(args.chunker, args.chunk_size)
    queries = load_queries(args.queries)
    store = build_knowledge_base(args.data_dir, embedder, chunker, "personal_benchmark")

    print(f"backend={backend} chunker={args.chunker} corpus_chunks={store.get_collection_size()}")
    if provider == "mock":
        print("WARNING: mock scores are a pipeline smoke test, not semantic retrieval evidence.")

    output: list[dict[str, Any]] = []
    relevant_top3 = 0
    for item in queries:
        results = store.search_with_filter(
            item["query"], top_k=args.top_k, metadata_filter=item["metadata_filter"]
        )
        found = any(result["metadata"].get("doc_id") == item["expected_doc_id"] for result in results)
        relevant_top3 += int(found)
        print(f"\n{item['id']}: {item['query']}")
        print(f"filter={item['metadata_filter']} expected={item['expected_doc_id']} top3_match={found}")
        serialized_results = []
        for rank, result in enumerate(results, start=1):
            metadata = result["metadata"]
            preview = " ".join(result["content"].split())[:240]
            print(
                f"  {rank}. score={result['score']:.6f} doc_id={metadata.get('doc_id')} "
                f"chunk={metadata.get('chunk_index')} | {preview}"
            )
            serialized_results.append(
                {
                    "rank": rank,
                    "score": result["score"],
                    "doc_id": metadata.get("doc_id"),
                    "chunk_index": metadata.get("chunk_index"),
                    "title": metadata.get("title"),
                    "content": result["content"],
                }
            )
        output.append({**item, "top3_match": found, "results": serialized_results})

    print(f"\nTop-3 expected-document matches: {relevant_top3}/5")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {"backend": backend, "chunker": args.chunker, "results": output},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
