# Job Radar — Domain Glossary

**Raw Record** — any file the user drops into `data/raw/` (wiki export, weekly report, old resume, annual review…). Never committed.

**Scan** — incremental extraction of Raw Records into the Master Resume. Tracked by `data/manifest.json` (file hash → scanned). Ends with a **Gap Interview**.

**Gap Interview** — questions the agent asks after a Scan to fill missing metrics/periods and resolve conflicts between sources.

**Master Resume** — `data/master.yaml`, the single source of truth. English text; every Achievement carries provenance (file + original-language quote). Fields marked `locked` are user-owned and never overwritten by a Scan.

**Achievement** — one atomic, citable fact (`id`, `text`, `metrics`, `tags`, `sources`). The unit that Tailoring selects and rewrites.

**Highlight** — an Achievement tagged `highlight` in the Master Resume (patent, award, promotion, launch result). Every Tailored Resume lists all Highlights in its Key Achievements section, whatever the job.

**Job Source** — an entry in `config/sources.yaml` (104 or a company careers site) with a fetch `method`: `api`, `fetch` or `browser`.

**Search Profile** — default filters in `config/profile.yaml` (industries, keywords, locations, seniority, `min_score`), overridable per `/search` run.

**Job Posting** — one opening, stored as `jobs/<company>-<id>.md` with the JD, Fit analysis and a `status`. Deduplicated by URL.

**Fit Score** — 0-100 rubric score of a Job Posting against the Master Resume (skills, seniority, industry, responsibilities), plus listed gaps.

**Status** — `new` → `shortlisted` → `tailored` → `applied` → `interview` → `rejected`/`offer`; or `ignored` (hidden from future searches).

**CV Template** — a `.docx` in `templates/` containing docxtpl Jinja tags.

**Tailored Resume** — English resume for one Job Posting, rendered to `output/<company>-<id>/resume.{docx,pdf}` with `changes.md`. Every bullet references a Master Resume Achievement `id`; nothing is invented.

_Avoid_: "CV" for the Master Resume (use "CV Template" only for the .docx layout); "job" alone when you mean Job Posting vs Job Source.
