# AGENTS Instructions

Scope: entire repository.

## Development rules for Codex

1. Keep MVP simple and modular; avoid premature abstractions.
2. Do not add OpenAI API integration unless explicitly requested.
3. Do not implement PDF parsing, email delivery, or Wiki publishing in MVP.
4. Keep default output paths stable:
   - `data/raw/YYYY-MM-DD.jsonl`
   - `reports/YYYY-MM-DD.md`
5. Every fetched paper record must include `priority="unscored"` until ranking is implemented.
6. Add/maintain tests for any changed behavior.
7. Never commit secrets or API keys.
8. Prefer pure functions in core modules (`filter_papers`, `render_report`) for testability.

## PR guidance

- PR title should start with: `[alpha-paper-radar]`
- PR body should include: summary, testing, and follow-ups.
