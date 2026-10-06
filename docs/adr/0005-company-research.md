# 5. Company research is a separate, cached step that never changes the Fit Score

Status: accepted (2026-10-06)

## Context
Besides the Fit Score, the user wants each job's pay (min / median / max), whether the company is growing or shrinking, and its work culture. That information is not in the JD: it is spread over 104's salary field, GoodJob, PTT, Dcard, Glassdoor, interview.tw, Levels.fyi, MOPS revenue and the news. Looking it up costs several searches and page reads per company, much more than scoring, and is per company, not per posting.

## Decision
- A separate `/research` skill writes a **Company Profile** to `companies/<slug>.md`. `/search` runs it only when asked (`research=N`: the top N distinct companies of that run).
- Each Company Profile section has its own `checked` date and TTL (Trend 90 days, culture 90, pay 180, in `scripts/companies.py`); only stale sections are researched again, and the new findings overwrite the old ones.
- Trend is one of growing / flat / shrinking / unknown with 2-3 dated, sourced pieces of evidence, mainly revenue YoY and layoff or hiring news. Culture is four fixed facets (hours, management, promotion, flexibility), each positive / mixed / negative / unknown with dated quotes. Pay keeps the posted range apart from reported pay (annual total comp, min / median / max, n); fewer than 3 reports is marked as indicative only, and role pay falls back to company-wide engineering pay, labelled as such.
- The Fit Score is never changed. Research adds a Company section, `pay`, `company_profile`, `[company]` risks and, with a stated reason, a new `interview_odds` to the Job Posting. `INDEX.md` shows Pay and Trend.
- Sources follow ADR 0003: public pages are fetched directly; pages behind a login or bot check are read in the user's Chrome with their own login, or skipped and named. No block is circumvented.
- The repo is public: `companies/` and `config/private.yaml` (the user's salary) are gitignored, like `jobs/`. Profiles quote forum and review sites, which should not be republished.

## Consequences
A plain `/search` stays as cheap as before, and a company researched once is reused by every posting and search until a section goes stale. Mixing company quality into the Fit Score would hide why a job scored as it did, so the two stay apart and the user weighs them. Reported pay is sparse for most Taiwan companies; the profile says how many reports a figure rests on rather than hiding it.
