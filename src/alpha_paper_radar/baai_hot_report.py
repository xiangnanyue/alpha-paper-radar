from __future__ import annotations

from datetime import datetime
from typing import Any


def _date_age_days(report_date: str, published: str) -> int | None:
    if not published:
        return None
    try:
        return (datetime.strptime(report_date, "%Y-%m-%d") - datetime.strptime(published, "%Y-%m-%d")).days
    except ValueError:
        return None


def _hotness_score(paper: dict[str, Any]) -> int:
    return int(paper.get("latest_hotness", paper.get("hotness", 0)))


def _rising_score(paper: dict[str, Any]) -> int:
    return int(paper.get("hotness_delta", 0))


def select_fast_rising(papers: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    rising = [p for p in papers if _rising_score(p) > 0]
    return sorted(rising, key=lambda p: (_rising_score(p), _hotness_score(p)), reverse=True)[:limit]


def select_latest(papers: list[dict[str, Any]], report_date: str, limit: int = 5) -> list[dict[str, Any]]:
    dated = [(p, _date_age_days(report_date, str(p.get("published", "")))) for p in papers]
    fresh = [p for p, age in dated if age is not None and age <= 14]
    return sorted(fresh, key=lambda p: (str(p.get("published", "")), _hotness_score(p)), reverse=True)[:limit]


def select_topic_matches(papers: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    matched = [p for p in papers if p.get("topics")]
    return sorted(matched, key=lambda p: (len(p.get("topics", [])), _hotness_score(p)), reverse=True)[:limit]


def _render_paper(paper: dict[str, Any], index: int) -> list[str]:
    lines = [f"### {index}) {paper.get('title', 'Untitled')}"]
    lines.append(f"- Hotness: **{_hotness_score(paper)}** (delta: **{_rising_score(paper):+d}**)")
    if paper.get("published"):
        lines.append(f"- Published: {paper.get('published')}")
    if paper.get("authors"):
        lines.append(f"- Authors: {', '.join(paper.get('authors', [])[:5])}")
    if paper.get("topics"):
        lines.append(f"- Matched topics: {', '.join(paper.get('topics', []))}")
    if paper.get("matched_keywords"):
        keyword_parts = [f"{topic}: {', '.join(words[:5])}" for topic, words in paper.get("matched_keywords", {}).items()]
        lines.append(f"- Matched keywords: {'; '.join(keyword_parts)}")
    if paper.get("detail_url"):
        lines.append(f"- BAAI: {paper.get('detail_url')}")
    if paper.get("pdf_url"):
        lines.append(f"- PDF: {paper.get('pdf_url')}")
    if paper.get("summary"):
        lines.append(f"- Summary: {paper.get('summary')}")
    lines.append("")
    return lines


def render_baai_hot_report(
    report_date: str,
    sections: dict[str, list[dict[str, Any]]],
    suppressed_duplicate_count: int,
    fetch_warnings: list[str] | None = None,
) -> str:
    new_papers = sections.get("new", [])
    updated_papers = sections.get("updated", [])
    all_papers = sorted(new_papers + updated_papers + sections.get("carryover", []), key=_hotness_score, reverse=True)
    fast_rising = select_fast_rising(all_papers)
    latest = select_latest(all_papers, report_date)
    topic_matches = select_topic_matches(all_papers)

    lines = [f"# BAAI Hot Paper Radar - {report_date}", "", "## Executive Summary"]
    lines.append(f"- New hot papers: **{len(new_papers)}**")
    lines.append(f"- Hotness-updated papers: **{len(updated_papers)}**")
    lines.append(f"- Suppressed unchanged papers: **{suppressed_duplicate_count}**")
    lines.append(f"- Fast-rising candidates: **{len(fast_rising)}**")
    lines.append(f"- Topic-matched candidates: **{len(topic_matches)}**")
    if fetch_warnings:
        lines.append(f"- Fetch warnings: **{len(fetch_warnings)}**")
    lines.append("")

    if fetch_warnings:
        lines.append("## Fetch Warnings")
        for warning in fetch_warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Fast Rising Papers")
    lines.extend(sum((_render_paper(p, i) for i, p in enumerate(fast_rising, 1)), []) if fast_rising else ["- No fast-rising papers detected.", ""])

    lines.append("## Latest Papers")
    lines.extend(sum((_render_paper(p, i) for i, p in enumerate(latest, 1)), []) if latest else ["- No papers published in the freshness window.", ""])

    lines.append("## Topic Matches")
    lines.extend(sum((_render_paper(p, i) for i, p in enumerate(topic_matches, 1)), []) if topic_matches else ["- No papers matched tracked topic keywords.", ""])

    lines.append("## New Papers")
    lines.extend(sum((_render_paper(p, i) for i, p in enumerate(new_papers, 1)), []) if new_papers else ["- No new hot papers.", ""])

    lines.append("## Updated Hotness")
    lines.extend(sum((_render_paper(p, i) for i, p in enumerate(updated_papers, 1)), []) if updated_papers else ["- No hotness updates.", ""])

    return "\n".join(lines).strip() + "\n"
