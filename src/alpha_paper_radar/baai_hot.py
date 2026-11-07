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

# Nuxt's inline payload is JavaScript, not JSON. Read only this literal field;
# consume quoted strings as units so text inside a title cannot become a field.
_EXACT_HOTNESS_RE = re.compile(
    r'\{id:"(?P<id>[\w-]+)"(?:(?:"(?:\\.|[^"\\])*")|[^"{}])*?'
    r'\bhotness_value:"(?P<hotness>\d+)"'
)


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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href is not None:
            text = _normalize_space("".join(self._current_text))
            if text:
                self.anchors.append({"href": self._current_href, "text": text})
            self._current_href = None
            self._current_text = []


class _PaperCardParser(HTMLParser):
    """Read fields within each card, preserving DOM boundaries and inline text."""

    _FIELDS = {
        "papers-home-header__title": "title",
        "paper-author-name": "authors",
        "papers-home-item-time": "published",
        "papers-home-hotness__num": "hotness",
        "expandable-text__plain": "summary",
    }
    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, Any]] = []
        self.scripts: list[str] = []
        self._stack: list[tuple[str, str | None, list[str]]] = []
        self._card: dict[str, Any] | None = None
        self._card_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if "papers-home-item" in classes:
            self._card = {"authors": []}
            self._card_depth = len(self._stack) + 1
        if self._card is not None and tag == "a":
            href = attributes.get("href") or ""
            if re.fullmatch(r"/paper/[\w-]+/?", urllib.parse.urlparse(href).path):
                self._card.setdefault("href", href)
        field = next((value for key, value in self._FIELDS.items() if key in classes), None)
        if tag not in self._VOID_TAGS:
            self._stack.append((tag, field, []))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._stack and self._stack[-1][0] == "script":
            self.scripts.append(data)
        for _, field, chunks in self._stack:
            if field:
                chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._stack or self._stack[-1][0] != tag:
            return
        _, field, chunks = self._stack.pop()
        if self._card is not None:
            value = _normalize_space("".join(chunks))
            if field == "authors":
                if value and value not in {"...", "…"}:
                    self._card["authors"].append(value)
            elif field:
                self._card[field] = value
            if len(self._stack) < self._card_depth:
                self.cards.append(self._card)
                self._card = None


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


def parse_baai_papers_html(html_text: str, source: str, fetched_at: str | None = None) -> list[dict[str, Any]]:
    parser = _PaperCardParser()
    parser.feed(html_text)
    if not parser.cards:
        raise ValueError("BAAI page contains no recognized paper cards")
    exact_hotness = {
        match.group("id"): int(match.group("hotness"))
        for match in _EXACT_HOTNESS_RE.finditer("\n".join(parser.scripts))
    }
    fetched = fetched_at or datetime.now(timezone.utc).isoformat()
    papers: list[dict[str, Any]] = []
    for card in parser.cards:
        title = card.get("title", "")
        detail_url = _absolute_url(card.get("href", ""))
        published = _parse_chinese_date(card.get("published", ""))
        if not title or not card.get("href") or not published:
            raise ValueError("BAAI paper card is missing title, URL or publication date")
        # Validate the calendar date, not just its shape.
        datetime.strptime(published, "%Y-%m-%d")
        paper_id = _stable_id(title, detail_url)
        hotness = exact_hotness.get(paper_id)
        if hotness is None:
            displayed = card.get("hotness", "")
            if not re.fullmatch(r"[0-9]+", displayed):
                raise ValueError(f"BAAI paper {paper_id} has no exact integer hotness: {displayed!r}")
            hotness = int(displayed)
        papers.append(
            {
                "id": paper_id,
                "source": source,
                "title": title,
                "authors": card["authors"],
                "published": published,
                "summary": card.get("summary", ""),
                "detail_url": detail_url,
                "pdf_url": "",
                "hotness": hotness,
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
