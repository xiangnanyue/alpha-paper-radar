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


def run(report_date: str) -> None:
    cfg = load_topics_config()
    topics = cfg["topics"]

    all_filtered: list[dict] = []
    by_topic: dict[str, list[dict]] = {}

    for topic_name, topic_cfg in topics.items():
        fetched = fetch_arxiv_papers(
            categories=topic_cfg["categories"],
            max_results=int(topic_cfg.get("max_results", 20)),
        )
        filtered = filter_papers_by_keywords(fetched, topic_cfg.get("keywords", []))
        for p in filtered:
            p["topic"] = topic_name
        by_topic[topic_name] = filtered
        all_filtered.extend(filtered)

    jsonl_path = Path("data/raw") / f"{report_date}.jsonl"
    report_path = Path("reports") / f"{report_date}.md"

    save_jsonl(all_filtered, jsonl_path)
    report_path.write_text(render_markdown_report(report_date, by_topic), encoding="utf-8")

    print(f"Saved {len(all_filtered)} papers -> {jsonl_path}")
    print(f"Generated report -> {report_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Paper Radar CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Fetch papers and generate report")
    run_parser.add_argument("--date", default="today", help="today or YYYY-MM-DD")

    args = parser.parse_args()

    if args.command == "run":
        run(resolve_date(args.date))


if __name__ == "__main__":
    main()
