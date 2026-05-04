from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def build_query(categories: list[str]) -> str:
    return " OR ".join(f"cat:{c}" for c in categories)


def fetch_arxiv_papers(
    categories: list[str],
    max_results: int = 20,
    max_retries: int = 2,
    backoff_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    params = {
        "search_query": build_query(categories),
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API_URL}?{urllib.parse.urlencode(params)}"

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_text = response.read().decode("utf-8")
            return parse_arxiv_feed(xml_text)
        except (urllib.error.URLError, TimeoutError, ET.ParseError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(backoff_seconds * (2**attempt))

    raise RuntimeError(f"Failed to fetch arXiv papers after retries: {last_error}") from last_error


def parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml_text)
    entries: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ns):
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        published = entry.findtext("atom:published", default="", namespaces=ns)
        updated = entry.findtext("atom:updated", default="", namespaces=ns)
        paper_id = entry.findtext("atom:id", default="", namespaces=ns)

        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", ns)]
        primary_category = ""
        primary = entry.find("arxiv:primary_category", ns)
        if primary is not None:
            primary_category = primary.attrib.get("term", "")
        if not primary_category and categories:
            primary_category = categories[0]

        entries.append(
            {
                "id": paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "updated": updated,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "priority": "unscored",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return entries
