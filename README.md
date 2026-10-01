# job-radar

Turn your own work records (wiki exports, weekly reports, old resumes, annual reviews…) into a sourced **Master Resume**, search 104 and company careers sites for matching openings, and render an English **Tailored Resume** per company from a `.docx` CV Template.

See [CONTEXT.md](CONTEXT.md) for the vocabulary and [docs/adr/](docs/adr/) for the key decisions.

## Prerequisites

- **[Claude Code](https://claude.com/claude-code)** — the workflow is a set of slash commands run inside Claude Code, opened in this folder. The Python scripts only do the deterministic steps ([ADR 0001](docs/adr/0001-claude-code-workflow.md)).
- **Python 3.11+**
- **Microsoft Word** — for PDF export (docx2pdf drives Word). Without it you still get the `.docx`.
- **Claude in Chrome** (optional) — needed for `browser` Job Sources (TSMC in the default config) and for 104 when it blocks scripted access, which is often. Without it those sources are skipped.

## Setup

```powershell
git clone https://github.com/snlienz/job-radar.git
cd job-radar
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest            # optional: check the install
```

Start Claude Code from a terminal where `.venv` is activated, so the commands' `python scripts/...` calls find the dependencies.

## Getting started

### 1. Add your records

Create `data/raw/` and drop in anything that describes your work: old resumes, self-reviews, weekly reports, wiki or Confluence exports. Subfolders are fine.

Supported formats: `.md`, `.txt`, `.docx`, `.pptx`, `.xlsx`, `.pdf`. Other files (legacy `.doc`, images…) are skipped, and so is any `attachments/` folder. Text files must be UTF-8. Save a `.doc` as `.docx` first.

### 2. Build the Master Resume — `/scan`

Claude extracts the new files, merges them into `data/master.yaml` (English text, each Achievement quoting its source), validates the result and then asks you **Gap Interview** questions about missing metrics, dates and conflicts. Answer them; it updates the file.

Read **`data/master.md`**, the human-readable version. Edit `data/master.yaml` directly to fix anything; add `locked: true` to an entry you want future scans never to touch. Add more files to `data/raw/` later and run `/scan` again; only new or changed files are read.

### 3. Set what you are looking for

Edit [`config/profile.yaml`](config/profile.yaml): keywords, locations, industries, seniority and the minimum Fit Score. **Set `keywords.include`**: it is empty by default, which searches every posting in your locations.

Job Sources live in [`config/sources.yaml`](config/sources.yaml) (104, NVIDIA and TSMC to start). Add a company with `/add-source <careers page url>`.

### 4. Find jobs — `/search`

Claude fetches postings, drops the ones that fail the profile, scores the rest against your Master Resume and writes one file per match to `jobs/<company>-<id>.md`, with the fit, the gaps and the full JD. Open **`jobs/INDEX.md`** for the list sorted by score.

Override the profile for one run: `/search keywords=firmware,embedded location=Hsinchu min_score=70`.

### 5. Make a resume — `/tailor jobs/<company>-<id>.md`

Claude picks the relevant Achievements, rewords them for the JD without inventing anything, validates every bullet against the Master Resume and renders `output/<company>-<id>/resume.docx` and `resume.pdf`.

Before you send it, read **`changes.md`** in the same folder: what was selected, rephrased and dropped, and which JD requirements your Master Resume cannot support. You can also pass a pasted JD or a URL instead of a job file.

### 6. Track your applications

Each job file has a `status` in its frontmatter:

`new` → `shortlisted` → `tailored` → `applied` → `interview` → `rejected` / `offer`, or `ignored`

`/tailor` sets `tailored`; change the others by editing the file. `ignored` hides the job from `INDEX.md` and from future searches. After editing, refresh the index:

```powershell
python scripts/search_jobs.py index
```

## Commands

| Command | What it does |
|---|---|
| `/scan` | Incrementally extract `data/raw/` into `data/master.yaml`, then ask about gaps |
| `/search [overrides]` | Fetch Job Postings from `config/sources.yaml`, filter by `config/profile.yaml`, score, write `jobs/` |
| `/tailor <job>` | Build a Tailored Resume for one Job Posting into `output/<company>-<id>/` |
| `/add-source <url>` | Add a company careers site and detect its fetch method |
| `/add-template <docx>` | Convert a plain `.docx` CV into a tagged CV Template in `templates/` |

## Where things are

| Path | What |
|---|---|
| `data/raw/` | Your records (input) |
| `data/master.yaml`, `data/master.md` | Master Resume and its readable view |
| `jobs/`, `jobs/INDEX.md` | Job Postings found by `/search` |
| `output/<company>-<id>/` | Tailored Resumes with `changes.md` |
| `config/` | Search Profile and Job Sources |
| `templates/` | CV Templates (`default.docx` is used unless you ask for another) |

## Privacy

`data/`, `jobs/` and `output/` are gitignored, so your records are never committed. They are read by Claude when you run the commands, so the text you put in `data/raw/` is sent to Claude as part of the conversation.
