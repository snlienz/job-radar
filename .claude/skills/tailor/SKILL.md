---
name: tailor
description: Build an English Tailored Resume (docx + pdf) for one Job Posting from the Master Resume. Use when the user runs /tailor, gives a job file or pasted JD and wants a resume for it.
---

# /tailor

Produce a Tailored Resume for one Job Posting. Read `CONTEXT.md` and `docs/adr/0002-master-resume-yaml-with-provenance.md` first. The schema is `schemas/tailored.schema.json`.

## 1. Get the job

The input is one of:
- a `jobs/<company>-<id>.md` file (use its slug `<company>-<id>`; its `status` is updated in step 5),
- a pasted JD or a URL (fetch it; if it needs a login or JS, ask the user to paste the text). There is no job file: derive a short slug yourself, e.g. `nvidia-firmware-lead`, and confirm it.

The JD may be in Chinese. **The output is always English.**

## 2. Select

Read `data/master.yaml` (all of it). Never read `data/raw/`; the Master Resume is the only source of facts.

Pick what this JD wants, keeping the resume to roughly one to two pages:
- **Achievements**: choose the ones most relevant to the JD's responsibilities and requirements, most relevant first within each experience entry. Drop weak or off-topic ones. Skip any tagged `do-not-use`.
- **Highlights**: every Achievement tagged `highlight` in the master (patents, awards, promotions, launch results), from any entry, whether or not it fits the JD. They are proof of past results and always go in.
- **Skills**: only skills that exist in the master's `skills`, ordered by relevance to the JD.
- **Education, certifications, languages**: copy entries unchanged from the master.
- **Summary / headline**: the only free text. Write 2-3 sentences supported by the Achievements you selected.

## 3. Write `output/<slug>/tailored.yaml`

Same shape as the master, with these differences:
- `job: <slug>` at the top.
- Every bullet is `{source_id, text}`, where `source_id` is the master Achievement `id` it came from, and the bullet sits under the same `experience` / `projects` entry as that Achievement.
- Each experience/project entry keeps its master `id`, `company`, `title`, `location`, `period` exactly. Do not change titles or dates.
- `highlights:` (rendered as Key Achievements, above Skills) is a list of `{source_id, text}` bullets, one per `highlight` Achievement, ordered by impact. Name the company in the text, e.g. `(Barco)`, since they sit outside the experience entries. A highlighted Achievement goes here, not under its experience entry.
- Each Achievement is used at most once.

Rephrasing rules (the point of tailoring, but never at the cost of truth):
- Reword with the JD's keywords where the Achievement really covers that thing. One bullet per Achievement; do not merge several into one.
- **Never invent.** Do not add a metric, tool, scope, team size or outcome that the Achievement's `text` / `metrics` does not state. Do not upgrade "contributed to" into "led". If a JD requirement has no supporting Achievement, leave it out of the resume and list it as a gap in `changes.md`.
- Keep bullets to one or two lines, starting with a verb.

## 4. Write `output/<slug>/changes.md`

Short, for the user to review:
- **Selected**: each `source_id` used and one line on why it matches the JD.
- **Rephrased**: for each bullet whose wording changed materially, the original master text and the new text.
- **Dropped**: Achievements considered but left out, with the reason.
- **Gaps**: JD requirements the master cannot support (candidates for a `/scan` Gap Interview).

## 5. Validate and render

```
python scripts/validate.py output/<slug>/tailored.yaml --master data/master.yaml
python scripts/render_resume.py output/<slug>/tailored.yaml templates/default.docx output/<slug>
```

Validation fails on a missing `highlight` Achievement, a bullet with no or unknown `source_id`, a bullet filed under the wrong entry, a `do-not-use` Achievement, a reused Achievement, a changed title/company/period, or a skill / education / certification / language that is not in the master. Fix every error and rerun; never edit the validator or the master to make it pass. Use another template from `templates/` if the user asks.

`render_resume.py` writes `resume.docx` and `resume.pdf` (PDF needs Word; if it fails, say so, the docx is still usable).

If there is a job file, set its status to `tailored`, unless it is already further along (`applied`, `interview`, `offer`, `rejected`):

```
python scripts/search_jobs.py status <slug> tailored
```

## 6. Report

Give the output folder, the gaps from `changes.md`, and anything the user should check by eye (rephrased bullets, the summary).
