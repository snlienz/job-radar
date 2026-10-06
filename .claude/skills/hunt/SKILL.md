---
name: hunt
description: Walk the user step by step through the job hunt (setup, search, Fit Gate, company research, Company Gate, tailor, applied?), working out from the files where they are and stopping for each decision. Use when the user runs /hunt, is new to the repo, or asks what to do next with their job search.
---

# /hunt

Read `CONTEXT.md` and `docs/adr/0006-guided-hunt.md` first. `/hunt` keeps no state of its own: every run works out from the files where the user is, does the next step with the existing skills (`/scan`, `/search`, `/research`, `/tailor`) and stops at each decision. Arguments are optional: `search` runs a new search (step 5) right after step 0, and any `key=value` overrides are passed on to `/search`.

Answer in the user's language (Traditional Chinese if they wrote in Chinese). Set every status with `python scripts/search_jobs.py status <key> <status>`, one call per job.

## 0. Setup

Check, in this order, and stop at the first blocker:
1. `config/profile.yaml` missing: copy `config/profile.example.yaml` to it and say so.
2. `data/master.yaml` missing: stop. Say there is no Master Resume yet: the user drops their records (old resumes, reviews, weekly reports) into `data/raw/` and runs `/scan`. If `data/raw/` already has files, offer to run `/scan` now.
3. `keywords.include` in `config/profile.yaml` empty and no `keywords=` override: ask which keywords to search for (suggest some from the Master Resume's skills). Offer to write them into `config/profile.yaml`; if the user declines, pass them as a `keywords=` override this run.

Then mention, without stopping:
- `config/private.yaml` missing: pay cannot be compared with theirs; copy `config/private.example.yaml` and fill it in.
- No Claude in Chrome tools (`mcp__claude-in-chrome__*`) in this session: 104 (often blocked), browser sources, Dcard and Glassdoor will be skipped.

## Where the user is

```
python scripts/search_jobs.py stages
```

It prints, highest score first, the jobs waiting on each step: `tailored` (step 1), `research` (step 2), `decide` (step 3) and `new` (step 4). Take the first step that has jobs, in that order; with none, go to step 5. Jobs closest to an application come first so a good job does not stall while new ones pile up. After a step, run `stages` again and carry on to the next step that has jobs, until the user stops or nothing is left to do but search again.

## 1. Applied?

List the `tailored` jobs (company, title, the resume in `output/<key>/`) and ask which ones the user has applied to. Set those to `applied`. Leave the rest; the user can say to skip this step.

## 2. Research

The `research` jobs are shortlisted but their company (`company_profile`) or department (`department`) is not researched yet. Group them by company. With more than 5 companies, list them and ask which to research now. For each company, run the `/research` skill (`.claude/skills/research/SKILL.md`) with the company name: it reuses a fresh Company Profile and researches the department of every shortlisted job of the company.

## 3. Company Gate

For each `decide` job read its `## Company` section and its Company Profile, and show a numbered table: score, interview odds, company, title, Trend, role pay, one line on culture (hours, management, promotion, flexibility, benefits; say `福利：未研究` for a profile written before the benefits facet, and that `/research <company> refresh` adds it), the department notes and every `[company]` risk.

Ask which jobs to apply for and which to drop. Run `/tailor jobs/<key>.md` for each chosen job, one at a time (it sets `tailored`). Set the dropped ones to `ignored`. The rest stay shortlisted and come back here next time.

## 4. Fit Gate

Show the `new` jobs ten at a time as a numbered table: score, interview odds, company, title, location, the one-sentence summary and the biggest gap from its Fit section. The user picks by number or says `more` for the next ten. Set picked jobs to `shortlisted`, then go to step 2 for them. Unpicked jobs stay `new`; only when the user says to drop the others ("其他都不要"), set the jobs shown so far that were not picked to `ignored`.

## 5. Search

Run the `/search` skill with the overrides (no `research=`: research only happens for jobs that pass the Fit Gate). Then go to step 4.

## Report

End every run with what changed (statuses set, companies researched, resumes made) and what the next `/hunt` will do first.
