from __future__ import annotations

from collections import defaultdict


def render_markdown_report(report_date: str, topic_to_papers: dict[str, list[dict]]) -> str:
    lines = [f"# Alpha Paper Radar - {report_date}", ""]

    total = sum(len(v) for v in topic_to_papers.values())
    lines.append(f"Total matched papers: **{total}**")
    lines.append("")

    for topic, papers in topic_to_papers.items():
        lines.append(f"## {topic}")
        if not papers:
            lines.append("- No matched papers.")
            lines.append("")
            continue

        for idx, p in enumerate(papers, start=1):
            authors = ", ".join(p.get("authors", [])[:5])
            lines.append(f"{idx}. **{p.get('title', 'Untitled')}**")
            lines.append(f"   - arXiv: {p.get('id', '')}")
            lines.append(f"   - Authors: {authors}")
            lines.append(f"   - Published: {p.get('published', '')}")
            lines.append(f"   - Priority: {p.get('priority', 'unscored')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
