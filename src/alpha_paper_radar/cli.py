from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from .config import load_topics_config
from .fetch_arxiv import fetch_arxiv_papers
from .filter_papers import filter_papers_by_keywords
from .registry import load_registry, merge_into_registry, save_registry
from .render_report import render_markdown_report
from .reporting import load_reporting_config
from .storage import save_jsonl


def resolve_date(raw: str) -> str:
    if raw == "today":
        return date.today().isoformat()
    return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()


def run(report_date: str, dry_run: bool = False, max_results_override: int | None = None) -> None:
    cfg = load_topics_config()
    _ = load_reporting_config()
    topics = cfg["topics"]

    unique_by_canonical: dict[str, dict] = {}
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

    jsonl_path = Path("data/raw") / f"{report_date}.jsonl"
    report_path = Path("reports") / f"{report_date}.md"

    all_filtered = list(unique_by_canonical.values())
    registry = load_registry()
    merged_registry, sections, suppressed_duplicate_count = merge_into_registry(registry, all_filtered, report_date)
    report_content = render_markdown_report(
        report_date,
        sections,
        suppressed_duplicate_count=suppressed_duplicate_count,
        failed_topics=failed_topics,
    )

    if dry_run:
        print(f"[DRY RUN] Unique papers: {len(all_filtered)}")
        print(report_content)
        return

    save_jsonl(all_filtered, jsonl_path)
    save_registry(merged_registry)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")

    print(f"Saved {len(all_filtered)} papers -> {jsonl_path}")
    print("Updated registry -> data/state/paper_registry.json")
    print(f"Generated report -> {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Paper Radar CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Fetch papers and generate report")
    run_parser.add_argument("--date", default="today", help="today or YYYY-MM-DD")
    run_parser.add_argument("--dry-run", action="store_true", help="Print report without writing files")
    run_parser.add_argument("--max-results-override", type=int, default=None, help="Override max_results for all topics")

    validate_parser = sub.add_parser("validate-config", help="Validate topic config file")
    validate_parser.add_argument("--path", default="config/topics.yaml", help="Path to topics config")

    args = parser.parse_args()

    if args.command == "run":
        run(resolve_date(args.date), dry_run=args.dry_run, max_results_override=args.max_results_override)
    elif args.command == "validate-config":
        cfg = load_topics_config(args.path)
        print(f"Config valid. Topics: {', '.join(cfg['topics'].keys())}")


if __name__ == "__main__":
    main()
