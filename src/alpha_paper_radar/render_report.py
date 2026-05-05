from __future__ import annotations

from datetime import datetime


def _parse_iso_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _build_reason_signals(paper: dict, report_date: str) -> list[str]:
    signals: list[str] = []
    title = str(paper.get("title", "")).lower()
    topics = paper.get("topics", [])

    keyword_map = {
        "llm": "LLM-related terms",
        "agent": "Agentic systems terms",
        "diffusion": "Diffusion-model terms",
        "transformer": "Transformer terms",
        "portfolio": "Portfolio-construction terms",
        "factor": "Factor-model terms",
        "time series": "Time-series terms",
        "panel": "Panel-data terms",
    }
    matched_terms = [label for kw, label in keyword_map.items() if kw in title]
    if matched_terms:
        signals.append(f"Matched core signals: {', '.join(matched_terms[:3])}")

    if len(topics) >= 2:
        signals.append(f"Relevant to {len(topics)} tracked topics")

    published = _parse_iso_date(str(paper.get("published", "")))
    updated = _parse_iso_date(str(paper.get("updated", "")))
    report_dt = datetime.strptime(report_date, "%Y-%m-%d")

    if published and (report_dt - published.replace(tzinfo=None)).days <= 3:
        signals.append(f"Newly published ({published.date().isoformat()})")

    if updated and (report_dt - updated.replace(tzinfo=None)).days <= 3:
        signals.append(f"Recently updated ({updated.date().isoformat()})")

    if int(paper.get("latest_version", 1)) > 1:
        signals.append(f"New version released (v{paper.get('latest_version')})")

    if not signals:
        signals.append("Matches tracked topic scope and category filters")

    return signals


def _derive_action(signals: list[str]) -> str:
    strong = any(s.startswith("Matched core signals") or s.startswith("Relevant to") for s in signals)
    fresh = any(s.startswith("Newly published") or s.startswith("Recently updated") for s in signals)
    if strong and fresh:
        return "Read now"
    if strong:
        return "Skim abstract"
    return "Track"


def _render_paper_lines(papers: list[dict], report_date: str, max_signals: int) -> list[str]:
    lines: list[str] = []
    for idx, p in enumerate(papers, start=1):
        authors = ", ".join(p.get("authors", [])[:5])
        canonical_id = p.get("canonical_id", "")
        signals = _build_reason_signals(p, report_date)
        action = _derive_action(signals)

        lines.append(f"### {idx}) {p.get('title', 'Untitled')}")
        lines.append(f"- Canonical ID: {canonical_id}")
        lines.append(f"- Authors: {authors}")
        lines.append(f"- Priority: {p.get('priority', 'unscored')}")
        if p.get("topics"):
            lines.append(f"- Matched topics: {', '.join(p.get('topics', []))}")
        lines.append(f"- Published/Updated: {p.get('published', '')} / {p.get('updated', '')}")
        lines.append(f"- Why recommended: {'; '.join(signals[:max_signals])}.")
        lines.append(f"- Action: {action}")
        lines.append("")
    return lines


def render_markdown_report(
    report_date: str,
    sections: dict[str, list[dict]],
    suppressed_duplicate_count: int,
    failed_topics: list[str] | None = None,
) -> str:
    new_papers = sections.get("new", [])
    updated_papers = sections.get("updated", [])
    carryover_papers = sections.get("carryover", [])

    top_picks = (new_papers + updated_papers)[:3]

    lines = [f"# Alpha Paper Radar - {report_date}", "", "## Executive Summary"]
    lines.append(f"- New papers: **{len(new_papers)}**")
    lines.append(f"- Updated papers: **{len(updated_papers)}**")
    lines.append(f"- Carry-over papers: **{len(carryover_papers)}**")
    lines.append(f"- Suppressed duplicates: **{suppressed_duplicate_count}**")
    if top_picks:
        lines.append("")
        lines.append("### Top picks")
        for idx, paper in enumerate(top_picks, start=1):
            reason = _build_reason_signals(paper, report_date)[0]
            lines.append(f"{idx}. **{paper.get('title', 'Untitled')}** — {reason}.")
    lines.append("")

    if failed_topics:
        lines.append("## Fetch Warnings")
        for topic in failed_topics:
            lines.append(f"- Failed to fetch topic: `{topic}`")
        lines.append("")

    lines.append("## New Papers")
    lines.extend(_render_paper_lines(new_papers, report_date, max_signals=4) if new_papers else ["- No new papers."])

    lines.append("## Updated Papers")
    lines.extend(_render_paper_lines(updated_papers, report_date, max_signals=3) if updated_papers else ["- No updated papers."])

    lines.append("## Carry-over Papers")
    lines.extend(_render_paper_lines(carryover_papers, report_date, max_signals=2) if carryover_papers else ["- No carry-over papers."])

    lines.append("## Suppressed Duplicates")
    lines.append(f"- Count: **{suppressed_duplicate_count}**")
    lines.append("")

    return "\n".join(lines).strip() + "\n"
