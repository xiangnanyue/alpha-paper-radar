from __future__ import annotations


def filter_papers_by_keywords(papers: list[dict], keywords: list[str]) -> list[dict]:
    if not keywords:
        return papers

    lowered_keywords = [k.lower() for k in keywords]
    result = []

    for paper in papers:
        text = f"{paper.get('title', '')} {paper.get('summary', '')}".lower()
        if any(k in text for k in lowered_keywords):
            result.append(paper)

    return result
