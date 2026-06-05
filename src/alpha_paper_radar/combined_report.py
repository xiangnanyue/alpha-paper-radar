from __future__ import annotations

from typing import Any, Protocol

from .render_report import _render_paper_lines


class ReportResult(Protocol):
    papers: list[dict[str, Any]]
    sections: dict[str, list[dict[str, Any]]]
    suppressed_duplicate_count: int
    report_content: str
    failed_topics: list[str] | None
    fetch_warnings: list[str] | None

    @property
    def has_new_or_updated(self) -> bool: ...


def _count(result: ReportResult, section_name: str) -> int:
    return len(result.sections.get(section_name, []))


def _demote_markdown_headings(markdown: str, levels: int = 1) -> list[str]:
    lines: list[str] = []
    for line in markdown.strip().splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("#"):
            lines.append("#" * levels + line)
        else:
            lines.append(line)
    return lines


def _render_arxiv_section(
    section_title: str,
    papers: list[dict[str, Any]],
    report_date: str,
    empty_message: str,
    max_signals: int,
) -> list[str]:
    lines = [f"## {section_title}"]
    lines.extend(_render_paper_lines(papers, report_date, max_signals=max_signals) if papers else [f"- {empty_message}"])
    lines.append("")
    return lines


def render_combined_report(report_date: str, arxiv_result: ReportResult, baai_result: ReportResult) -> str:
    """Render the one-file daily report that combines arXiv and BAAI outputs."""
    lines = [f"# Alpha Paper Radar - {report_date}", "", "## Executive Summary"]
    lines.append(f"- arXiv new papers: **{_count(arxiv_result, 'new')}**")
    lines.append(f"- arXiv updated papers: **{_count(arxiv_result, 'updated')}**")
    lines.append(f"- arXiv carry-over papers: **{_count(arxiv_result, 'carryover')}**")
    lines.append(f"- arXiv suppressed duplicates: **{arxiv_result.suppressed_duplicate_count}**")
    lines.append(f"- BAAI new hot papers: **{_count(baai_result, 'new')}**")
    lines.append(f"- BAAI hotness-updated papers: **{_count(baai_result, 'updated')}**")
    lines.append(f"- BAAI suppressed unchanged papers: **{baai_result.suppressed_duplicate_count}**")
    if arxiv_result.failed_topics:
        lines.append(f"- arXiv failed topics: **{len(arxiv_result.failed_topics)}**")
    if baai_result.fetch_warnings:
        lines.append(f"- BAAI fetch warnings: **{len(baai_result.fetch_warnings)}**")
    lines.append("")

    if arxiv_result.failed_topics or baai_result.fetch_warnings:
        lines.append("## Fetch Warnings")
        for topic in arxiv_result.failed_topics or []:
            lines.append(f"- Failed to fetch arXiv topic: `{topic}`")
        for warning in baai_result.fetch_warnings or []:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(
        _render_arxiv_section(
            "New Papers",
            arxiv_result.sections.get("new", []),
            report_date,
            "No new arXiv papers.",
            max_signals=4,
        )
    )
    lines.extend(
        _render_arxiv_section(
            "Updated Papers",
            arxiv_result.sections.get("updated", []),
            report_date,
            "No updated arXiv papers.",
            max_signals=3,
        )
    )
    lines.extend(
        _render_arxiv_section(
            "Carry-over Papers",
            arxiv_result.sections.get("carryover", []),
            report_date,
            "No carry-over arXiv papers.",
            max_signals=2,
        )
    )

    lines.append("## Suppressed Duplicates")
    lines.append(f"- arXiv count: **{arxiv_result.suppressed_duplicate_count}**")
    lines.append(f"- BAAI unchanged count: **{baai_result.suppressed_duplicate_count}**")
    lines.append("")

    lines.append("## BAAI Hot Papers")
    lines.extend(_demote_markdown_headings(baai_result.report_content, levels=1))
    lines.append("")

    return "\n".join(lines).strip() + "\n"
