from __future__ import annotations

from pathlib import Path


DEFAULT_REPORTING = {
    "dedupe_window_days": 14,
    "carryover_cooldown_days": 7,
    "max_carryover_papers": 3,
    "min_new_papers_for_email": 3,
}


def load_reporting_config(path: str | Path = "config/reporting.toml") -> dict[str, int]:
    cfg_path = Path(path)
    if not cfg_path.exists():
        return dict(DEFAULT_REPORTING)

    merged = dict(DEFAULT_REPORTING)
    for raw_line in cfg_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in merged:
            merged[key] = int(value.strip())
    return merged
