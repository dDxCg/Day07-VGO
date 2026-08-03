"""Clean crawler output and keep the manifest aligned with scripts/urls.csv."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
URLS_PATH = ROOT / "scripts" / "urls.csv"
DATA_DIR = ROOT / "data" / "k3_university"
MANIFEST_PATH = DATA_DIR / "sources.csv"
CUTOFF_MARKERS = {"Gửi bình luận"}


def clean_markdown(path: Path) -> tuple[int, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    closing = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if closing is None:
        raise ValueError(f"Missing YAML front matter: {path}")

    header = lines[: closing + 1]
    body = lines[closing + 1 :]
    cutoff = next(
        (index for index, line in enumerate(body) if line.strip() in CUTOFF_MARKERS),
        len(body),
    )
    body = body[:cutoff]

    cleaned: list[str] = []
    previous_blank = False
    for raw in body:
        line = raw.rstrip().replace("\u00a0", " ")
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        cleaned.append("" if is_blank else line)
        previous_blank = is_blank

    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    output = "\n".join(header + [""] + cleaned) + "\n"
    path.write_text(output, encoding="utf-8")
    return len(lines), len(output.splitlines())


def load_allowed_documents() -> list[str]:
    with URLS_PATH.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    document_ids = [row["doc_id"].strip() for row in rows]
    if not document_ids or any(not document_id for document_id in document_ids):
        raise ValueError("Every urls.csv row must have a non-empty doc_id")
    if len(document_ids) != len(set(document_ids)):
        raise ValueError("Duplicate doc_id in urls.csv")
    return document_ids


def filter_manifest(allowed_ids: list[str]) -> None:
    with MANIFEST_PATH.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row.get("doc_id") in allowed_ids]
    if not fieldnames:
        raise ValueError("Manifest has no header")
    if {row["doc_id"] for row in rows} != set(allowed_ids):
        raise ValueError("Manifest does not contain every urls.csv document")

    rows.sort(key=lambda row: allowed_ids.index(row["doc_id"]))
    for row in rows:
        row["file_path"] = f"data/k3_university/{row['doc_id']}.md"
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    allowed_ids = load_allowed_documents()
    for document_id in allowed_ids:
        path = DATA_DIR / f"{document_id}.md"
        before, after = clean_markdown(path)
        print(f"Cleaned {path.name}: {before} -> {after} lines")
    filter_manifest(allowed_ids)
    print(f"Manifest contains {len(allowed_ids)} current documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
