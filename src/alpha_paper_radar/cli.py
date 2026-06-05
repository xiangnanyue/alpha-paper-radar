from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .baai_hot import DAILY_SPEC, WEEKLY_SPEC, dedupe_baai_papers, fetch_baai_hot_papers, match_topics
from .baai_hot_registry import load_baai_registry, merge_baai_hot_papers, save_baai_registry
from .baai_hot_report import render_baai_hot_report
from .combined_report import render_combined_report
from .config import load_topics_config
from .fetch_arxiv import fetch_arxiv_papers
from .filter_papers import filter_papers_by_keywords
from .registry import load_registry, merge_into_registry, save_registry
from .render_report import render_markdown_report
from .reporting import load_reporting_config
from .storage import save_jsonl


@dataclass
class DailyResult:
    papers: list[dict[str, Any]]
    registry: dict[str, dict[str, Any]]
    sections: dict[str, list[dict[str, Any]]]
    suppressed_duplicate_count: int
    report_content: str
    jsonl_path: Path
    report_path: Path | None = None
    failed_topics: list[str] | None = None
    fetch_warnings: list[str] | None = None

    @property
    def has_new_or_updated(self) -> bool:
        return bool(self.sections.get("new") or self.sections.get("updated"))


def resolve_date(raw: str) -> str:
    if raw == "today":
        return date.today().isoformat()
    if len(raw) == 8 and raw.isdigit():
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()
    return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()


def _build_arxiv_result(
    report_date: str,
    cfg: dict[str, Any],
    max_results_override: int | None = None,
) -> DailyResult:
    topics = cfg["topics"]
    unique_by_canonical: dict[str, dict[str, Any]] = {}
    failed_topics: list[str] = []

    for topic_name, topic_cfg in topics.items():
        try:
            fetched = fetch_arxiv_papers(
                categories=topic_cfg["categories"],
                max_results=max_results_override or int(topic_cfg.get("max_results", 20)),
            )
            filtered = filter_papers_by_keywords(fetched, topic_cfg.get("keywords", []))
        except Exception as exc:
            failed_topics.append(topic_name)
            print(f"[WARN] Topic '{topic_name}' failed: {exc}")
            continue

        for paper in filtered:
            paper_id = str(paper.get("id", "")).strip()
            if not paper_id:
                continue
            existing = unique_by_canonical.get(paper_id)
            if existing:
                existing["topics"] = sorted(set(existing.get("topics", [])) | {topic_name})
                continue
            copied = dict(paper)
            copied["topic"] = topic_name
            copied["topics"] = [topic_name]
            unique_by_canonical[paper_id] = copied

    all_filtered = list(unique_by_canonical.values())
    registry = load_registry()
    merged_registry, sections, suppressed_duplicate_count = merge_into_registry(registry, all_filtered, report_date)
    report_content = render_markdown_report(
        report_date,
        sections,
        suppressed_duplicate_count=suppressed_duplicate_count,
        failed_topics=failed_topics,
    )
    return DailyResult(
        papers=all_filtered,
        registry=merged_registry,
        sections=sections,
        suppressed_duplicate_count=suppressed_duplicate_count,
        report_content=report_content,
        jsonl_path=Path("data/raw") / f"{report_date}.jsonl",
        report_path=Path("reports") / f"{report_date}.md",
        failed_topics=failed_topics,
    )


def _build_baai_hot_result(report_date: str, cfg: dict[str, Any], skip_pdf: bool = False) -> DailyResult:
    fetched: list[dict[str, Any]] = []
    fetch_warnings: list[str] = []
    for spec in [DAILY_SPEC, WEEKLY_SPEC]:
        try:
            fetched.extend(fetch_baai_hot_papers(spec, enrich_pdf=not skip_pdf))
        except Exception as exc:
            fetch_warnings.append(f"Failed to fetch BAAI {spec.name} list: {exc}")
            print(f"[WARN] Failed to fetch BAAI {spec.name} list: {exc}")
    papers = match_topics(dedupe_baai_papers(fetched), cfg)

    registry = load_baai_registry()
    merged_registry, sections, suppressed_duplicate_count = merge_baai_hot_papers(registry, papers, report_date)
    report_content = render_baai_hot_report(report_date, sections, suppressed_duplicate_count, fetch_warnings=fetch_warnings)
    return DailyResult(
        papers=papers,
        registry=merged_registry,
        sections=sections,
        suppressed_duplicate_count=suppressed_duplicate_count,
        report_content=report_content,
        jsonl_path=Path("data/baai_hot/raw") / f"{report_date}.jsonl",
        report_path=Path("reports/baai_hot") / f"{report_date}.md",
        fetch_warnings=fetch_warnings,
    )


def run(
    report_date: str,
    dry_run: bool = False,
    max_results_override: int | None = None,
    skip_baai_pdf: bool = False,
) -> None:
    cfg = load_topics_config()
    _ = load_reporting_config()

    arxiv_result = _build_arxiv_result(report_date, cfg, max_results_override=max_results_override)
    baai_result = _build_baai_hot_result(report_date, cfg, skip_pdf=skip_baai_pdf)
    should_generate_report = arxiv_result.has_new_or_updated or baai_result.has_new_or_updated
    report_path = Path("reports") / f"{report_date}.md"
    combined_report = render_combined_report(report_date, arxiv_result, baai_result)

    if dry_run:
        print(f"[DRY RUN] Unique arXiv papers: {len(arxiv_result.papers)}")
        print(f"[DRY RUN] BAAI unique hot papers: {len(baai_result.papers)}")
        print(combined_report)
        return

    save_jsonl(arxiv_result.papers, arxiv_result.jsonl_path)
    save_registry(arxiv_result.registry)
    save_jsonl(baai_result.papers, baai_result.jsonl_path)
    save_baai_registry(baai_result.registry)

    if should_generate_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(combined_report, encoding="utf-8")
    else:
        report_path.unlink(missing_ok=True)

    print(f"Saved {len(arxiv_result.papers)} papers -> {arxiv_result.jsonl_path}")
    print("Updated registry -> data/state/paper_registry.json")
    print(f"Saved {len(baai_result.papers)} BAAI papers -> {baai_result.jsonl_path}")
    print("Updated BAAI registry -> data/baai_hot/state/paper_registry.json")
    if should_generate_report:
        print(f"Generated combined report -> {report_path}")
    else:
        print("Skipped report generation (arXiv new/updated=0 and BAAI new/updated=0)")


def run_baai_hot(report_date: str, dry_run: bool = False, skip_pdf: bool = False) -> None:
    cfg = load_topics_config()
    result = _build_baai_hot_result(report_date, cfg, skip_pdf=skip_pdf)

    if dry_run:
        print(f"[DRY RUN] BAAI unique hot papers: {len(result.papers)}")
        print(result.report_content)
        return

    save_jsonl(result.papers, result.jsonl_path)
    save_baai_registry(result.registry)
    if result.report_path is None:
        raise RuntimeError("BAAI report path is not configured")
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    result.report_path.write_text(result.report_content, encoding="utf-8")

    print(f"Saved {len(result.papers)} BAAI papers -> {result.jsonl_path}")
    print("Updated BAAI registry -> data/baai_hot/state/paper_registry.json")
    print(f"Generated BAAI report -> {result.report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Paper Radar CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Fetch arXiv and BAAI hot papers, then generate one combined report")
    run_parser.add_argument("--date", default="today", help="today or YYYY-MM-DD")
    run_parser.add_argument("--dry-run", action="store_true", help="Print report without writing files")
    run_parser.add_argument("--max-results-override", type=int, default=None, help="Override max_results for all arXiv topics")
    run_parser.add_argument("--skip-baai-pdf", action="store_true", help="Skip BAAI detail-page PDF enrichment")

    baai_parser = sub.add_parser("run-baai-hot", help="Fetch BAAI hot papers and generate separate report")
    baai_parser.add_argument("--date", default="today", help="today or YYYY-MM-DD")
    baai_parser.add_argument("--dry-run", action="store_true", help="Print report without writing files")
    baai_parser.add_argument("--skip-pdf", action="store_true", help="Skip detail-page PDF enrichment")

    validate_parser = sub.add_parser("validate-config", help="Validate topic config file")
    validate_parser.add_argument("--path", default="config/topics.yaml", help="Path to topics config")

    args = parser.parse_args()

    if args.command == "run":
        run(
            resolve_date(args.date),
            dry_run=args.dry_run,
            max_results_override=args.max_results_override,
            skip_baai_pdf=args.skip_baai_pdf,
        )
    elif args.command == "run-baai-hot":
        run_baai_hot(resolve_date(args.date), dry_run=args.dry_run, skip_pdf=args.skip_pdf)
    elif args.command == "validate-config":
        cfg = load_topics_config(args.path)
        print(f"Config valid. Topics: {', '.join(cfg['topics'].keys())}")


if __name__ == "__main__":
    main()
