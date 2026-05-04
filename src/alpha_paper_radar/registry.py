from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ARXIV_ID_RE = re.compile(r"(?:.*/abs/)?(?P<id>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$")


def parse_arxiv_id(raw_id: str) -> tuple[str, int]:
    m = ARXIV_ID_RE.search(raw_id.strip())
    if not m:
        return raw_id.strip(), 1
    return m.group("id"), int(m.group("version") or 1)


def compute_content_hash(paper: dict[str, Any]) -> str:
    payload = {
        "title": paper.get("title", ""),
        "authors": paper.get("authors", []),
        "categories": paper.get("categories", []),
        "primary_category": paper.get("primary_category", ""),
        "published": paper.get("published", ""),
        "updated": paper.get("updated", ""),
        "summary": paper.get("summary", ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def load_registry(path: str | Path = "data/state/paper_registry.json") -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_registry(registry: dict[str, dict[str, Any]], path: str | Path = "data/state/paper_registry.json") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return p


def merge_into_registry(
    registry: dict[str, dict[str, Any]], papers: list[dict[str, Any]], report_date: str
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], int]:
    new_papers: list[dict[str, Any]] = []
    updated_papers: list[dict[str, Any]] = []
    suppressed_duplicates = 0

    for paper in papers:
        canonical_id, version = parse_arxiv_id(str(paper.get("id", "")))
        if not canonical_id:
            continue

        content_hash = compute_content_hash(paper)
        record = registry.get(canonical_id)
        if record is None:
            record = {
                "canonical_id": canonical_id,
                "latest_version": version,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "categories": paper.get("categories", []),
                "primary_category": paper.get("primary_category", ""),
                "published": paper.get("published", ""),
                "updated": paper.get("updated", ""),
                "first_seen_date": report_date,
                "last_seen_date": report_date,
                "last_reported_date": report_date,
                "report_count": 1,
                "topics": sorted(paper.get("topics", [])),
                "content_hash": content_hash,
                "priority": "unscored",
            }
            registry[canonical_id] = record
            new_papers.append(dict(record))
            continue

        changed = record.get("updated") != paper.get("updated", "") or record.get("content_hash") != content_hash
        record["latest_version"] = max(int(record.get("latest_version", 1)), version)
        record["title"] = paper.get("title", record.get("title", ""))
        record["authors"] = paper.get("authors", record.get("authors", []))
        record["categories"] = paper.get("categories", record.get("categories", []))
        record["primary_category"] = paper.get("primary_category", record.get("primary_category", ""))
        record["published"] = paper.get("published", record.get("published", ""))
        record["updated"] = paper.get("updated", record.get("updated", ""))
        record["last_seen_date"] = report_date
        record["topics"] = sorted(set(record.get("topics", [])) | set(paper.get("topics", [])))
        record["priority"] = "unscored"

        if changed:
            record["content_hash"] = content_hash
            record["last_reported_date"] = report_date
            record["report_count"] = int(record.get("report_count", 0)) + 1
            updated_papers.append(dict(record))
        else:
            suppressed_duplicates += 1

    return registry, {"new": new_papers, "updated": updated_papers, "carryover": []}, suppressed_duplicates
