# Job Radar — Domain Glossary

**Raw Record** — any file the user drops into `data/raw/` (wiki export, weekly report, old resume, annual review…). Never committed.

**Scan** — incremental extraction of Raw Records into the Master Resume. Tracked by `data/manifest.json` (file hash → scanned). Ends with a **Gap Interview**.

**Gap Interview** — questions the agent asks after a Scan to fill missing metrics/periods and resolve conflicts between sources.

**Master Resume** — `data/master.yaml`, the single source of truth. English text; every Achievement carries provenance (file + original-language quote). Fields marked `locked` are user-owned and never overwritten by a Scan.

**Achievement** — one atomic, citable fact (`id`, `text`, `metrics`, `tags`, `sources`). The unit that Tailoring selects and rewrites.

**Highlight** — an Achievement tagged `highlight` in the Master Resume (patent, award, promotion, launch result). Every Tailored Resume lists all Highlights in its Key Achievements section, whatever the job.

**Work Area** — a named group of one experience entry's Achievements in the Master Resume (`areas`, e.g. capture engine, Smart Meeting Flow). A Tailored Resume shows bullets under their area. A `core` Work Area is the main body of work in that job and appears in every Tailored Resume, so no resume hides what the job really was.

**Job Source** — an entry in `config/sources.yaml` (104 or a company careers site) with a fetch `method`: `api`, `fetch` or `browser`.

**Search Profile** — default filters in `config/profile.yaml` (industries, keywords, locations, seniority, `min_score`), overridable per `/search` run. Include keywords match the title or JD; exclude keywords match the title only. `/search url=<careers page>` scores one page's jobs without the include filter.

**Job Posting** — one opening, stored as `jobs/<company>-<id>.md` with the JD, Fit analysis and a `status`. Deduplicated by URL.

**Fit Score** — 0-100 rubric score of a Job Posting against the Master Resume (skills, seniority, industry, responsibilities), plus listed strengths and gaps, and optionally an estimated interview-odds range, risks (such as overqualification, salary or commute) and prep actions.

**Company Profile** — `companies/<slug>.md`, what `/research` found about one company: its **Trend** (growing / flat / shrinking / unknown, from revenue YoY and layoff or hiring news), its culture on four facets (hours, management, promotion, flexibility) and its reported pay, each with dated, sourced evidence and its own `checked` date so stale sections are researched again. Keyed by the company's English name, with `aliases` (Chinese name, local subsidiary); a Taiwan branch shares its parent's profile. Gitignored.

**Company research** — what `/research` adds to a Job Posting: a Company section, a `pay` estimate for that role, `[company]` risks and, if they change the odds, a new `interview_odds`. It never changes the Fit Score, which only measures resume-to-JD fit. Pay is compared with the gitignored `config/private.yaml` salary.

**Status** — `new` → `shortlisted` → `tailored` → `applied` → `interview` → `rejected`/`offer`; or `ignored` (hidden from future searches).

**CV Template** — a `.docx` in `templates/` containing docxtpl Jinja tags.

**Tailored Resume** — English resume for one Job Posting, rendered to `output/<company>-<id>/resume.{docx,pdf}` with `changes.md`. Every bullet references a Master Resume Achievement `id`; nothing is invented.

_Avoid_: "CV" for the Master Resume (use "CV Template" only for the .docx layout); "job" alone when you mean Job Posting vs Job Source.
