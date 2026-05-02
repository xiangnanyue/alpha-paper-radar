from __future__ import annotations

from pathlib import Path
from typing import Any


def _parse_inline_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip('"').strip("'") for item in inner.split(",")]


def load_topics_config(path: str | Path = "config/topics.yaml") -> dict[str, Any]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    topics: dict[str, dict[str, Any]] = {}
    current_topic: str | None = None

    for raw_line in cfg_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "topics:":
            continue

        if line.startswith("  ") and stripped.endswith(":") and not line.startswith("    "):
            current_topic = stripped[:-1]
            topics[current_topic] = {}
            continue

        if current_topic and line.startswith("    ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in {"categories", "keywords"}:
                topics[current_topic][key] = _parse_inline_list(value)
            elif key == "max_results":
                topics[current_topic][key] = int(value)

    if not topics:
        raise ValueError("topics.yaml must contain a non-empty 'topics' mapping")

    return {"topics": topics}
