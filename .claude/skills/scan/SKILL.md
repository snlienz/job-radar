---
name: scan
description: Incrementally turn Raw Records in data/raw/ into the Master Resume data/master.yaml, then run a Gap Interview. Use when the user runs /scan, adds new files to data/raw/, or asks to update or rebuild the master resume.
---

# /scan

Build `data/master.yaml` from Raw Records. Read `CONTEXT.md` and `docs/adr/0002-master-resume-yaml-with-provenance.md` first. The schema is `schemas/master.schema.json`.

## 1. Extract

```
python scripts/extract.py
```

Prints `new` / `changed` files and writes text to `data/extracted/<path>.txt`. Files already in `data/manifest.json` are skipped, but extract never writes the manifest: a file only counts as scanned after you commit it (step 4), so an interrupted scan reports the same files again next time. `attachments/` folders and non-text formats (png, mov…) are ignored. A `failed` line is a file that could not be read (corrupt, password-protected, or text that is neither UTF-8 nor Big5): tell the user which file and why, and carry on with the rest. If nothing is new or changed, say so and stop.

Read **only** the extracted text of new/changed files, never the whole of `data/extracted/`.

## 2. Merge into data/master.yaml

Create the file if missing (`basics` + `experience` are required). Otherwise edit in place.

Rules:
- **English text, original-language provenance.** `text` is English; every Achievement has `sources[{file, quote}]` where `file` is the path relative to `data/raw/` (exactly as printed by extract) and `quote` is a **verbatim** excerpt in the original language. Never paraphrase a quote.
- **One atomic fact per Achievement** (what was done + result). `id` is a unique kebab-case slug across the whole file. `metrics` only holds numbers that appear in a source.
- **Never invent.** No metric, title, date, or scope that a source does not state. Unsure → `confidence: low` and raise it in the Gap Interview.
- **Dedupe.** The same work reported in several records (weekly report, wiki, self-review) becomes one Achievement with several `sources`, not several Achievements.
- **Conflicts.** If sources disagree (dates, numbers, titles), keep the best-supported value, set `conflict` to a one-line explanation, and ask in the Gap Interview.
- **Never touch `locked`.** Anything with `locked: true`, and anything under a `locked` experience/project/basics, is read-only. To add evidence to a locked Achievement, put the suggestion in the Gap Interview instead.
- **Personal data.** Only fill `basics` fields the schema has. Do not copy date of birth, ID numbers, or home address.
- Put each Achievement under the right `experience` entry (company + period) or `projects`. If the entry has `areas` (Work Areas), add the new id to the area it belongs to; an Achievement tagged `highlight` stays out of areas. Create or rename areas, and set `core`, only with the user's agreement. Fill `skills` (with `evidence` ids) and `education` / `certifications` / `languages` when sources state them.

## 3. Reading order (large data sets)

Prefer high-signal sources and stop reading a source type once it stops adding new facts:
1. Legacy resumes and self-reviews: companies, titles, periods, education, headline accomplishments. Do these first to create the `experience` skeleton.
2. Weekly reports: month-level evidence and metrics. Read per file and skim for deliverables and results.
3. Wiki pages: design docs and plans give scope, ownership and technical depth. Judge by title; skim the page to decide whether it holds a personal accomplishment.
4. Tool logs, such as Copilot chat history under `copilot-usage/`, are large and noisy. Use them only to corroborate skills or tools actually used. Do not mine them for Achievements.

Process in batches (one folder or year at a time), write the merge to disk after each batch, and run step 4 before continuing, so partial progress is never lost.

## 4. Validate and render

```
python scripts/validate.py data/master.yaml
python scripts/render_master.py
```

Fix every error before continuing, then commit the batch's files as scanned (paths exactly as printed by extract, only the files merged in this batch):

```
python scripts/extract.py --commit <path> [<path> ...]
```

Validation checks the schema, that Achievement ids are unique, that each source `file` exists in `data/raw/`, that each `quote` appears verbatim (whitespace-insensitive) in that file's extracted text, and that every skill `evidence` id exists. `render_master.py` writes `data/master.md` for the user to read.

## 5. Gap Interview

After the merge, list what is missing and ask the user. Ask in the user's language. Group the questions, ask at most ~8 at a time, and put the highest-impact ones first:
- Achievements with no metric or an unclear result.
- Missing or unclear periods, titles, or scope (team size, ownership).
- Every `conflict` you set.
- Suggestions for `locked` items.

Apply the answers to `data/master.yaml`, mark user-confirmed values `confidence: high`, and re-run validate and render. Finish by reporting: files scanned, Achievements added or changed, open questions left. If Achievements were added and `python scripts/stories.py status` prints `missing` or `stale`, mention that `/prep` builds the Story Bank or adds them to it.
