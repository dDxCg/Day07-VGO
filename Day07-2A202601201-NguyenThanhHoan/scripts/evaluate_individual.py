"""Run the five individual retrieval benchmarks with the local E5 model."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from ingest import build_knowledge_base
from src import KnowledgeBaseAgent, LocalEmbedder, RecursiveChunker


DATA_DIR = ROOT / "data" / "k3_university"
OUTPUT_PATH = ROOT / "report" / "individual_evaluation.json"
STOPWORDS = {
    "bao",
    "các",
    "của",
    "cho",
    "được",
    "gì",
    "khi",
    "là",
    "một",
    "những",
    "sinh",
    "theo",
    "tại",
    "trong",
    "và",
    "về",
}


BENCHMARKS = [
    {
        "id": 1,
        "query": "ĐHQGHN đang triển khai bao nhiêu chương trình đào tạo đại học, thạc sĩ và tiến sĩ?",
        "gold_answer": "190 chương trình đại học, 198 chương trình thạc sĩ và 118 chương trình tiến sĩ.",
        "expected_doc_id": "vnu-training-overview",
        "evidence_patterns": [r"190 chương trình.*198 chương trình.*118 chương trình"],
        "metadata_filter": None,
    },
    {
        "id": 2,
        "query": "Theo tài liệu được đánh dấu hết hiệu lực, quỹ học bổng khuyến khích học tập tối thiểu bằng bao nhiêu phần trăm tổng thu học phí?",
        "gold_answer": "Tối thiểu 15% tổng thu học phí từ sinh viên đại học hệ chính quy.",
        "expected_doc_id": "vnu-scholarship-management-regulation",
        "evidence_patterns": [r"15% tổng thu học phí"],
        "metadata_filter": None,
    },
    {
        "id": 3,
        "query": "Đại học Quốc gia Hà Nội có 01 trường Trung học Cơ sở và 04 trường Trung học Phổ thông nào?",
        "gold_answer": "ĐHQGHN có 01 trường THCS và 04 trường THPT.",
        "expected_doc_id": "vnu-secondary-and-high-school-education",
        "evidence_patterns": [r"01 trường Trung học Cơ sở.*04\s*trường Trung học Phổ thông"],
        "metadata_filter": None,
    },
    {
        "id": 4,
        "query": "Chương trình Quỹ UOB cho sinh viên vay tối đa bao nhiêu, lãi suất và thời hạn trả nợ thế nào?",
        "gold_answer": "Tối đa 10.000.000 đồng, lãi suất 0%; bắt đầu trả sau 6 tháng kể từ khi tốt nghiệp và trả dần trong 30 tháng, theo 30 kỳ hàng tháng.",
        "expected_doc_id": "vnu-student-loans",
        "evidence_patterns": [
            r"10\.000\.000",
            r"Lãi suất:\s*0",
            r"Sau 6 tháng.*30 tháng",
        ],
        "metadata_filter": {"audience": "student"},
    },
    {
        "id": 5,
        "query": "Những sinh viên nào là đối tượng tham dự Ngày hội việc làm Samsung của ĐHQGHN?",
        "gold_answer": "Sinh viên năm thứ 3 và năm cuối thuộc nhóm ngành Kinh tế–Luật–Ngoại ngữ hoặc Khoa học–Kỹ thuật–Công nghệ tại các đơn vị đào tạo của ĐHQGHN.",
        "expected_doc_id": "vnu-career-support",
        "evidence_patterns": [r"sinh viên năm thứ 3 và năm cuối"],
        "metadata_filter": None,
    },
]


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", text.lower(), flags=re.UNICODE)
        if len(token) > 1 and token not in STOPWORDS
    }


def extractive_llm(prompt: str) -> str:
    """Small deterministic local stand-in: select evidence across top-k chunks."""
    context_match = re.search(r"NGỮ CẢNH:\n(.*?)\n\nCÂU HỎI:\n", prompt, flags=re.DOTALL)
    question_match = re.search(r"CÂU HỎI:\n(.*?)\n\nTRẢ LỜI:", prompt, flags=re.DOTALL)
    if not context_match or not question_match:
        return "Chưa đủ thông tin trong ngữ cảnh."

    question_tokens = tokens(question_match.group(1))
    candidates = []
    seen = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", context_match.group(1)):
        sentence = sentence.strip()
        normalized = " ".join(sentence.lower().split())
        if not sentence or sentence.startswith("[Đoạn ") or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(sentence)
    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (-len(tokens(item[1]) & question_tokens), len(item[1])),
    )
    selected = sorted(ranked[:12], key=lambda item: item[0])
    return " ".join(sentence for _, sentence in selected) or "Chưa đủ thông tin trong ngữ cảnh."


class FilteredStoreView:
    def __init__(self, store, metadata_filter: dict | None) -> None:
        self.store = store
        self.metadata_filter = metadata_filter

    def search(self, query: str, top_k: int = 3):
        if self.metadata_filter:
            return self.store.search_with_filter(
                query,
                top_k=top_k,
                metadata_filter=self.metadata_filter,
            )
        return self.store.search(query, top_k=top_k)


def summarize(text: str, limit: int = 260) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    embedder = LocalEmbedder(model_name=model_name)
    chunker = RecursiveChunker(chunk_size=800)
    store = build_knowledge_base(
        DATA_DIR,
        embedding_fn=embedder,
        chunker=chunker,
        collection_name="individual_vnu_evaluation",
    )

    results = []
    for benchmark in BENCHMARKS:
        view = FilteredStoreView(store, benchmark["metadata_filter"])
        top_results = view.search(benchmark["query"], top_k=3)
        expected_evidence = "\n".join(
            result["content"]
            for result in top_results
            if result["metadata"].get("doc_id") == benchmark["expected_doc_id"]
        )
        relevant_in_top3 = all(
            re.search(pattern, expected_evidence, flags=re.IGNORECASE | re.DOTALL)
            for pattern in benchmark["evidence_patterns"]
        )
        agent = KnowledgeBaseAgent(store=view, llm_fn=extractive_llm)
        answer = agent.answer(benchmark["query"], top_k=3)
        results.append(
            {
                **{key: value for key, value in benchmark.items() if key != "evidence_patterns"},
                "relevant_in_top3": relevant_in_top3,
                "top_results": [
                    {
                        "rank": rank,
                        "doc_id": result["metadata"].get("doc_id"),
                        "chunk_index": result["metadata"].get("chunk_index"),
                        "score": round(result["score"], 6),
                        "summary": summarize(result["content"]),
                    }
                    for rank, result in enumerate(top_results, start=1)
                ],
                "agent_answer": summarize(answer, limit=1200),
            }
        )

    payload = {
        "embedding_model": model_name,
        "embedding_dimension": len(embedder.embed_query("kiểm tra")),
        "chunker": "RecursiveChunker(chunk_size=800)",
        "collection_size": store.get_collection_size(),
        "relevant_top3_count": sum(item["relevant_in_top3"] for item in results),
        "benchmarks": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
