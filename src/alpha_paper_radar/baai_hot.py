from __future__ import annotations

import hashlib
import html
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

BAAI_PAPERS_URL = "https://hub.baai.ac.cn/papers"
BAAI_BASE_URL = "https://hub.baai.ac.cn"

_DATE_RE = re.compile(r"(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日")
_HOTNESS_RE = re.compile(r"(?P<hotness>\d+)\s*热度")


@dataclass(frozen=True)
class BaaiFetchSpec:
    name: str
    time: str
    min_hotness: int


DAILY_SPEC = BaaiFetchSpec(name="daily", time="day", min_hotness=50)
WEEKLY_SPEC = BaaiFetchSpec(name="weekly", time="week", min_hotness=500)


def build_baai_hot_url(time_window: str) -> str:
    if time_window in {"day", "today"}:
        return BAAI_PAPERS_URL
    return f"{BAAI_PAPERS_URL}?{urllib.parse.urlencode({'model': 'hotness', 'time': time_window})}"


class _PaperListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.text_chunks.append(data.strip())
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = _normalize_space("".join(self._current_text))
            if text:
                self.anchors.append({"href": self._current_href, "text": text})
            self._current_href = None
            self._current_text = []


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _absolute_url(href: str) -> str:
    return urllib.parse.urljoin(BAAI_BASE_URL, href)


def _parse_chinese_date(value: str) -> str:
    match = _DATE_RE.search(value)
    if not match:
        return ""
    return f"{int(match.group('year')):04d}-{int(match.group('month')):02d}-{int(match.group('day')):02d}"


def _stable_id(title: str, detail_url: str) -> str:
    parsed_path = urllib.parse.urlparse(detail_url).path.rstrip("/")
    if parsed_path.startswith("/paper/"):
        return parsed_path.rsplit("/", 1)[-1]
    return hashlib.sha256(title.lower().encode("utf-8")).hexdigest()[:16]


def _extract_authors(title_text: str, title: str) -> list[str]:
    tail = title_text.removeprefix(title).strip(" ,")
    tail = tail.replace("...", "")
    return [name.strip() for name in tail.split(" , ") if name.strip()]


def _split_title_and_authors(anchor_text: str, following_text: str) -> tuple[str, list[str]]:
    date_match = _DATE_RE.search(following_text)
    prefix = following_text[: date_match.start()].strip() if date_match else anchor_text
    title_text = prefix if prefix and anchor_text.startswith(prefix) else anchor_text
    title = title_text
    authors: list[str] = []
    separators = ["  ", " , "]
    for sep in separators:
        if sep in title_text:
            left, right = title_text.split(sep, 1)
            if len(left) >= 6:
                title = left.strip(" ,")
                authors = [name.strip() for name in right.replace("...", "").split(" , ") if name.strip()]
                break
    if not authors and title != title_text:
        authors = _extract_authors(title_text, title)
    return title.strip(), authors


def _extract_summary(following_text: str) -> str:
    date_match = _DATE_RE.search(following_text)
    hotness_match = _HOTNESS_RE.search(following_text)
    if not date_match:
        return ""
    start = date_match.end()
    end = hotness_match.start() if hotness_match else len(following_text)
    return following_text[start:end].strip()


def parse_baai_papers_html(html_text: str, source: str, fetched_at: str | None = None) -> list[dict[str, Any]]:
    parser = _PaperListParser()
    parser.feed(html_text)
    full_text = _normalize_space(" ".join(parser.text_chunks))
    fetched = fetched_at or datetime.now(timezone.utc).isoformat()
    papers: list[dict[str, Any]] = []

    paper_anchors = [a for a in parser.anchors if "/paper/" in a["href"]]
    for index, anchor in enumerate(paper_anchors):
        anchor_text = _normalize_space(anchor["text"])
        if not anchor_text:
            continue
        next_anchor_text = _normalize_space(paper_anchors[index + 1]["text"]) if index + 1 < len(paper_anchors) else ""
        start = full_text.find(anchor_text)
        if start < 0:
            continue
        end = full_text.find(next_anchor_text, start + len(anchor_text)) if next_anchor_text else len(full_text)
        following = full_text[start:end if end > start else len(full_text)]
        hotness_match = _HOTNESS_RE.search(following)
        if not hotness_match:
            continue
        detail_url = _absolute_url(anchor["href"])
        title, authors = _split_title_and_authors(anchor_text, following)
        papers.append(
            {
                "id": _stable_id(title, detail_url),
                "source": source,
                "title": title,
                "authors": authors,
                "published": _parse_chinese_date(following),
                "summary": _extract_summary(following),
                "detail_url": detail_url,
                "pdf_url": "",
                "hotness": int(hotness_match.group("hotness")),
                "priority": "unscored",
                "fetched_at": fetched,
            }
        )
    return papers


def extract_pdf_url(html_text: str) -> str:
    parser = _PaperListParser()
    parser.feed(html_text)
    for anchor in parser.anchors:
        href = anchor["href"]
        text = anchor["text"].lower()
        if href.lower().endswith(".pdf") or text == "pdf":
            return _absolute_url(href)
    match = re.search(r"https?://[^\"'<>\s]+\.pdf", html_text)
    return match.group(0) if match else ""


def fetch_url(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "alpha-paper-radar/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_baai_hot_papers(
    spec: BaaiFetchSpec,
    *,
    enrich_pdf: bool = True,
    max_retries: int = 2,
    backoff_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    url = build_baai_hot_url(spec.time)
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            html_text = fetch_url(url)
            papers = [p for p in parse_baai_papers_html(html_text, source=spec.name) if p["hotness"] >= spec.min_hotness]
            if enrich_pdf:
                for paper in papers:
                    try:
                        paper["pdf_url"] = extract_pdf_url(fetch_url(str(paper["detail_url"])))
                    except Exception:
                        paper["pdf_url"] = ""
            return papers
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(backoff_seconds * (2**attempt))
    raise RuntimeError(f"Failed to fetch BAAI {spec.name} hot papers after retries: {last_error}") from last_error


def dedupe_baai_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for paper in papers:
        paper_id = str(paper.get("id", "")).strip()
        if not paper_id:
            continue
        existing = by_id.get(paper_id)
        if existing is None:
            copied = dict(paper)
            copied["sources"] = [paper.get("source", "")]
            by_id[paper_id] = copied
            continue
        existing["hotness"] = max(int(existing.get("hotness", 0)), int(paper.get("hotness", 0)))
        existing["sources"] = sorted(set(existing.get("sources", [])) | {str(paper.get("source", ""))})
        for key in ["summary", "pdf_url", "published", "detail_url"]:
            if not existing.get(key) and paper.get(key):
                existing[key] = paper[key]
    return sorted(by_id.values(), key=lambda p: int(p.get("hotness", 0)), reverse=True)


def match_topics(papers: list[dict[str, Any]], topics_config: dict[str, Any]) -> list[dict[str, Any]]:
    topics = topics_config.get("topics", {})
    result: list[dict[str, Any]] = []
    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
        matched: list[str] = []
        matched_keywords: dict[str, list[str]] = {}
        for topic_name, topic_cfg in topics.items():
            keywords = [str(k) for k in topic_cfg.get("keywords", [])]
            hits = [kw for kw in keywords if kw.lower() in text]
            if hits:
                matched.append(topic_name)
                matched_keywords[topic_name] = hits
        copied = dict(paper)
        copied["topics"] = sorted(matched)
        copied["matched_keywords"] = matched_keywords
        result.append(copied)
    return result
