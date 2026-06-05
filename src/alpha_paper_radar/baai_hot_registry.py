from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BAAI_REGISTRY_PATH = Path("data/baai_hot/state/paper_registry.json")


def load_baai_registry(path: str | Path = BAAI_REGISTRY_PATH) -> dict[str, dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_baai_registry(registry: dict[str, dict[str, Any]], path: str | Path = BAAI_REGISTRY_PATH) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return p


def merge_baai_hot_papers(
    registry: dict[str, dict[str, Any]], papers: list[dict[str, Any]], report_date: str
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]], int]:
    new_papers: list[dict[str, Any]] = []
    updated_papers: list[dict[str, Any]] = []
    suppressed_duplicates = 0

    for paper in papers:
        paper_id = str(paper.get("id", "")).strip()
        if not paper_id:
            continue
        hotness = int(paper.get("hotness", 0))
        record = registry.get(paper_id)
        observation = {
            "date": report_date,
            "hotness": hotness,
            "sources": paper.get("sources", [paper.get("source", "")]),
        }
        if record is None:
            record = {
                "id": paper_id,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "published": paper.get("published", ""),
                "summary": paper.get("summary", ""),
                "detail_url": paper.get("detail_url", ""),
                "pdf_url": paper.get("pdf_url", ""),
                "first_seen_date": report_date,
                "last_seen_date": report_date,
                "first_hotness": hotness,
                "latest_hotness": hotness,
                "peak_hotness": hotness,
                "hotness_delta": 0,
                "observations": [observation],
                "topics": sorted(paper.get("topics", [])),
                "matched_keywords": paper.get("matched_keywords", {}),
                "priority": "unscored",
            }
            registry[paper_id] = record
            new_papers.append(dict(record))
            continue

        old_hotness = int(record.get("latest_hotness", 0))
        last_observation = record.get("observations", [])[-1] if record.get("observations") else {}
        changed = old_hotness != hotness or record.get("summary", "") != paper.get("summary", "") or record.get("pdf_url", "") != paper.get("pdf_url", "")
        record.update(
            {
                "title": paper.get("title", record.get("title", "")),
                "authors": paper.get("authors", record.get("authors", [])),
                "published": paper.get("published", record.get("published", "")),
                "summary": paper.get("summary", record.get("summary", "")),
                "detail_url": paper.get("detail_url", record.get("detail_url", "")),
                "pdf_url": paper.get("pdf_url", record.get("pdf_url", "")),
                "last_seen_date": report_date,
                "latest_hotness": hotness,
                "peak_hotness": max(int(record.get("peak_hotness", 0)), hotness),
                "hotness_delta": hotness - old_hotness,
                "topics": sorted(set(record.get("topics", [])) | set(paper.get("topics", []))),
                "matched_keywords": {**record.get("matched_keywords", {}), **paper.get("matched_keywords", {})},
                "priority": "unscored",
            }
        )
        if last_observation.get("date") == report_date:
            record["observations"][-1] = observation
        else:
            record.setdefault("observations", []).append(observation)
        if changed:
            updated_papers.append(dict(record))
        else:
            suppressed_duplicates += 1

    return registry, {"new": new_papers, "updated": updated_papers, "carryover": []}, suppressed_duplicates
