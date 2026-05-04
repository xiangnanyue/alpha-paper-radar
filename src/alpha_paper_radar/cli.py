from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from .config import load_topics_config
from .fetch_arxiv import fetch_arxiv_papers
from .filter_papers import filter_papers_by_keywords
from .render_report import render_markdown_report
from .storage import save_jsonl


def resolve_date(raw: str) -> str:
    if raw == "today":
        return date.today().isoformat()
    return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()


def run(report_date: str, dry_run: bool = False, max_results_override: int | None = None) -> None:
    cfg = load_topics_config()
    topics = cfg["topics"]

    unique_by_id: dict[str, dict] = {}
    by_topic: dict[str, list[dict]] = {}
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
            by_topic[topic_name] = []
            print(f"[WARN] Topic '{topic_name}' failed: {exc}")
            continue

        current_topic_papers: list[dict] = []
        for paper in filtered:
            paper_id = paper.get("id", "")
            if not paper_id:
                continue
            if paper_id in unique_by_id:
                existing = unique_by_id[paper_id]
                existing_topics = set(existing.get("topics", []))
                existing_topics.add(topic_name)
                existing["topics"] = sorted(existing_topics)
                current_topic_papers.append(existing)
            else:
                copied = dict(paper)
                copied["topic"] = topic_name
                copied["topics"] = [topic_name]
                unique_by_id[paper_id] = copied
                current_topic_papers.append(copied)

        by_topic[topic_name] = current_topic_papers

    jsonl_path = Path("data/raw") / f"{report_date}.jsonl"
    report_path = Path("reports") / f"{report_date}.md"
    all_filtered = list(unique_by_id.values())
    report_content = render_markdown_report(report_date, by_topic, failed_topics=failed_topics)

    if dry_run:
        print(f"[DRY RUN] Unique papers: {len(all_filtered)}")
        print(report_content)
        return

    save_jsonl(all_filtered, jsonl_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding="utf-8")

    print(f"Saved {len(all_filtered)} papers -> {jsonl_path}")
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
