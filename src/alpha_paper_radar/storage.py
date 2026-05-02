from __future__ import annotations

import json
from pathlib import Path


def save_jsonl(papers: list[dict], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for paper in papers:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")

    return path
