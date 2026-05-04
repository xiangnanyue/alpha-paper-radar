from __future__ import annotations


def render_markdown_report(report_date: str, topic_to_papers: dict[str, list[dict]], failed_topics: list[str] | None = None) -> str:
    lines = [f"# Alpha Paper Radar - {report_date}", ""]

    total = sum(len(v) for v in topic_to_papers.values())
    lines.append(f"Total matched papers: **{total}**")
    lines.append("")

    if failed_topics:
        lines.append("## Fetch Warnings")
        for topic in failed_topics:
            lines.append(f"- Failed to fetch topic: `{topic}`")
        lines.append("")

    for topic, papers in topic_to_papers.items():
        lines.append(f"## {topic}")
        if not papers:
            lines.append("- No matched papers.")
            lines.append("")
            continue

        sorted_papers = sorted(papers, key=lambda p: p.get("published", ""), reverse=True)
        for idx, p in enumerate(sorted_papers, start=1):
            authors = ", ".join(p.get("authors", [])[:5])
            paper_id = p.get("id", "")
            lines.append(f"{idx}. **[{p.get('title', 'Untitled')}]({paper_id})**")
            lines.append(f"   - arXiv: {paper_id}")
            lines.append(f"   - Authors: {authors}")
            lines.append(f"   - Published: {p.get('published', '')}")
            lines.append(f"   - Priority: {p.get('priority', 'unscored')}")
            if p.get("topics"):
                lines.append(f"   - Topics: {', '.join(p.get('topics', []))}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
