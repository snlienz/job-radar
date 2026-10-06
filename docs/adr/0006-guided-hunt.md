# 6. A stateless guided /hunt with two decision gates

Status: accepted (2026-10-06)

## Context
The commands cover the whole job hunt (`/scan`, `/search`, `/research`, `/tailor`), but a user has to know their order, and the repo is meant to be cloned by others who start with no Master Resume and no Search Profile. `/search research=N` chains search and research, but it picks companies by Fit Score alone; the user's own habit is to judge the fit first and look into a company only once a job is worth it, then decide again after reading about pay, growth and culture.

## Decision
- A `/hunt` skill is the entry point. It keeps no state: each run reads the files (`data/master.yaml`, `config/profile.yaml`, the job files' `status`, `company_profile` and `department`) through `search_jobs.py stages`, does the next step with the existing skills and stops for each decision. A hunt interrupted for days picks up where the files say it is, and status changes made by hand are respected.
- Step 0 blocks on what makes the rest meaningless (no Master Resume, no include keywords) and only warns about what degrades it (no `config/private.yaml`, no Claude in Chrome).
- Two gates, with no new status: the **Fit Gate** moves `new` jobs the user picks to `shortlisted`; research runs only for shortlisted jobs; the **Company Gate** sends the chosen ones to `/tailor` and the dropped ones to `ignored`. A shortlisted job counts as researched once it has both `company_profile` and `department`. A tailored job is asked about once per run ("applied?").
- Steps run in the order applied? → research → Company Gate → Fit Gate → new search, so a job close to an application does not stall while new ones pile up.
- Company research gains a fifth culture facet, benefits (福利). Workplace bullying stays inside the management facet, but one specific report from the last 2 years becomes a `[company]` risk marked 單一來源 until a second source agrees. Existing profiles get benefits only when their culture section goes stale or on `refresh`; until then it shows as 未研究.
- Department notes (forum and Google reports about the job's department or BU) are researched for shortlisted jobs only and written to the job file, not the Company Profile.
- `config/profile.yaml` becomes per-user and gitignored; `config/profile.example.yaml` is committed and `/hunt` copies it when missing.

## Consequences
`/hunt` adds no logic the other skills lack, so each step can still be run on its own. Telling "shortlisted, not researched" from "researched, undecided" depends on the `department` field, which `/research` sets only for shortlisted jobs. Department reports are sparse and short-lived; kept per job they cannot be mistaken for the company's general picture. Clones that pulled `config/profile.yaml` before this change lose it from git on the next pull and must keep or recreate their own copy.
