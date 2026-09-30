# 2. Master Resume is structured English YAML with provenance; tailoring never invents facts

Status: accepted (2026-09-30)

## Context
Raw Records are largely Chinese; Tailored Resumes are always English. An LLM rewriting freely from documents can fabricate or exaggerate.

## Decision
- `data/master.yaml` (schema: `schemas/master.schema.json`) holds atomic Achievements in English, each with `sources[{file, quote}]` quoting the original text.
- Scans are incremental (hash manifest) and never overwrite `locked` fields.
- A Tailored Resume may reorder, select and rephrase, but every bullet must reference an Achievement `id`. `scripts/validate.py` rejects any bullet without one.
- Output language is fixed to English regardless of the JD language.

## Consequences
Translation happens once and is reviewed once. Every claim in any resume can be traced back to a Raw Record.
