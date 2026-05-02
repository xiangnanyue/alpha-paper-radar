from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"


def build_query(categories: list[str]) -> str:
    return " OR ".join(f"cat:{c}" for c in categories)


def fetch_arxiv_papers(categories: list[str], max_results: int = 20) -> list[dict[str, Any]]:
    params = {
        "search_query": build_query(categories),
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = requests.get(ARXIV_API_URL, params=params, timeout=30)
    response.raise_for_status()
    return parse_arxiv_feed(response.text)


def parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]:
    ns = {"atom": "http://www.w3.org/2005/Atom"}
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

        entries.append(
            {
                "id": paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "updated": updated,
                "authors": authors,
                "categories": categories,
                "priority": "unscored",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return entries
