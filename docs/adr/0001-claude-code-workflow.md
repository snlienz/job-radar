# 1. Claude Code skills drive the workflow; Python does only deterministic work

Status: accepted (2026-09-30)

## Context
Scanning mixed-language documents, judging job fit and rewriting bullets are judgment tasks. File extraction, HTTP fetching, schema validation and .docx rendering are deterministic.

## Decision
The user runs slash-command skills in `.claude/skills/` (`/scan`, `/search`, `/tailor`, `/add-source`, `/add-template`). The agent does the judgment work; it calls small Python scripts in `scripts/` for deterministic steps. No LLM API calls from Python. Runs are manual — no scheduling.

## Consequences
- No LLM pipeline to maintain; behaviour changes by editing SKILL.md files.
- Scripts stay testable with pytest and plain fixtures.
- Browser-only Job Sources depend on Claude in Chrome being available during `/search`.
