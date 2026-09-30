# job-radar

Turn your own work records (wiki exports, weekly reports, old resumes, annual reviews…) into a sourced **Master Resume**, search 104 and company careers sites for matching openings, and render an English **Tailored Resume** per company from a `.docx` CV Template.

See [CONTEXT.md](CONTEXT.md) for the vocabulary and [docs/adr/](docs/adr/) for the key decisions.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

PDF export uses docx2pdf, which needs Microsoft Word installed.

## Workflow (Claude Code slash commands)

| Command | What it does |
|---|---|
| `/scan` | Incrementally extract `data/raw/` into `data/master.yaml`, then ask about gaps |
| `/search [overrides]` | Fetch Job Postings from `config/sources.yaml`, filter by `config/profile.yaml`, score, write `jobs/` |
| `/tailor <job>` | Build a Tailored Resume for one Job Posting into `output/<company>-<id>/` |
| `/add-source <url>` | Add a company careers site and detect its fetch method |
| `/add-template <docx>` | Convert a plain `.docx` CV into a tagged CV Template |

`data/`, `jobs/` and `output/` are gitignored — your personal records never leave the machine through git.
