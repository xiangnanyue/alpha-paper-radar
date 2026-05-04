from __future__ import annotations


def _render_paper_lines(papers: list[dict]) -> list[str]:
    lines: list[str] = []
    for idx, p in enumerate(papers, start=1):
        authors = ", ".join(p.get("authors", [])[:5])
        canonical_id = p.get("canonical_id", "")
        lines.append(f"{idx}. **{p.get('title', 'Untitled')}**")
        lines.append(f"   - Canonical ID: {canonical_id}")
        lines.append(f"   - Latest Version: v{p.get('latest_version', 1)}")
        lines.append(f"   - Authors: {authors}")
        lines.append(f"   - Published: {p.get('published', '')}")
        lines.append(f"   - Updated: {p.get('updated', '')}")
        lines.append(f"   - Priority: {p.get('priority', 'unscored')}")
        if p.get("topics"):
            lines.append(f"   - Topics: {', '.join(p.get('topics', []))}")
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

    lines = [f"# Alpha Paper Radar - {report_date}", "", "## Executive Summary"]
    lines.append(f"- New papers: **{len(new_papers)}**")
    lines.append(f"- Updated papers: **{len(updated_papers)}**")
    lines.append(f"- Carry-over papers: **{len(carryover_papers)}**")
    lines.append(f"- Suppressed duplicates: **{suppressed_duplicate_count}**")
    lines.append("")

    if failed_topics:
        lines.append("## Fetch Warnings")
        for topic in failed_topics:
            lines.append(f"- Failed to fetch topic: `{topic}`")
        lines.append("")

    lines.append("## New Papers")
    lines.extend(_render_paper_lines(new_papers) if new_papers else ["- No new papers."])
    lines.append("")

    lines.append("## Updated Papers")
    lines.extend(_render_paper_lines(updated_papers) if updated_papers else ["- No updated papers."])
    lines.append("")

    lines.append("## Carry-over Papers")
    lines.extend(_render_paper_lines(carryover_papers) if carryover_papers else ["- No carry-over papers."])
    lines.append("")

    lines.append("## Suppressed Duplicates")
    lines.append(f"- Count: **{suppressed_duplicate_count}**")
    lines.append("")

    return "\n".join(lines).strip() + "\n"
