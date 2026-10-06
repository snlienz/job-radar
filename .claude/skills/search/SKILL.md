---
name: search
description: Find Job Postings from the configured Job Sources (or one careers page with url=), filter them by the Search Profile, score each against the Master Resume and list them in jobs/, optionally researching the top companies (research=N). Use when the user runs /search, optionally with overrides like keywords=firmware min_score=70, or gives a careers page URL to score.
---

# /search

Read `CONTEXT.md` and `docs/adr/0003-per-source-fetch-method.md` first. Arguments are optional `key=value` overrides of `config/profile.yaml`: `keywords=a,b` (must match title or JD), `exclude=x,y`, `location=Taipei,Hsinchu`, `industries=…`, `seniority=…`, `min_score=70`. Pass them unchanged to the scripts below. Work in `data/search/<YYYY-MM-DD>/` (gitignored).

`research=N` is not a profile override: take it out before passing the rest on. It runs company research after step 5 (see step 6).

If `config/profile.yaml` is missing, copy `config/profile.example.yaml` to it first. If neither `config/profile.yaml` `keywords.include` nor a `keywords=` override gives a keyword, stop and ask the user for some before fetching: without one every posting in the locations is fetched and scored. The exception is URL mode below.

### URL mode: `/search url=<careers page>`

The user already has the page, so skip keyword searching. `url=` is not a profile override: take it out of the arguments before passing the rest on.
- Step 1 becomes `python scripts/fetch_jobs.py --url <url> [--name <Company>] --out data/search/<date>/postings.json`. It takes every job link in the page's section, so a page that is itself a posting with a sidebar of the others works. Pass `--name` when the host name is not the company name. A `BLOCKED` result (104 company pages usually are) or 0 postings (a JS-rendered page) means you read the page through the browser as in step 2.
- Before step 3, fill in every empty `location` in `postings.json` from its `jd_text` (e.g. a "工作地點" or "Location" line) so the location filter can work.
- In step 3, add `keywords=` to the overrides so the include filter is off. Excluded titles, locations and jobs already in `jobs/` still drop out.
- Remove any candidate that is not a single job, such as a listing, benefits or contact page, before scoring. Treat a posting tied to a past event (e.g. "2024 Open House") as likely stale and say so in `risks`.

## 1. Fetch (api / fetch sources)

```
python scripts/fetch_jobs.py [overrides] --out data/search/<date>/postings.json
```

Searches each keyword × location, fetches full JDs and writes `{postings, browser, errors}`. Postings are normalized: `source, company, id, title, location, url, jd_text, posted_at`. Add `--only <name>` for one source and `--limit N` to change the per-query cap (default 40).

The script prints `BLOCKED` for a source that refused scripted access (104 sits behind a Cloudflare bot challenge and often does), and lists `browser` sources. Do not try to get around a block with other clients or headers; handle those sources in step 2. Any other `ERROR` is a real failure: tell the user and carry on with the rest.

## 2. Fetch (browser sources and blocked sources)

For every source in `browser` plus every `blocked` error, drive the user's Chrome with Claude in Chrome (read the `chrome-browser` skill first). For each source:
- Open the source `url`, search each keyword (and location if the site has the filter), and walk the result pages until you have about as many postings as the script would fetch (stop at ~40 per keyword).
- Open each posting and read its title, location, URL, posted date and full JD text.
- Append each as an object with exactly the same fields to `postings` in `postings.json`. `id` is the site's job/requisition id (or the last URL segment), `company` the hiring company (the source name for a single-company site), `posted_at` as `YYYY-MM-DD` or `null`.

If the browser is unavailable or a site needs a login the user has not done, say which source was skipped and why.

## 3. Hard filter

```
python scripts/search_jobs.py filter data/search/<date>/postings.json --out data/search/<date>/candidates.json [overrides]
```

Drops postings with no include keyword in title/JD, an exclude keyword in the title, an unwanted location, a URL already in `jobs/` (any status) or a status of `ignored`, and duplicates within the run. Each candidate gets a `key` (`<company>-<id>` slug). The dropped list goes to stderr; mention the counts, not every line.

## 4. Score

Read `data/master.yaml` once, and `config/profile.yaml` for `industries` and `seniority`. For each candidate, read its `jd_text` and score 0-100:

| Dimension | Points | Question |
|---|---|---|
| Skills | 40 | Does the Master Resume show the required and preferred skills, with evidence? |
| Responsibilities | 25 | Is the day-to-day work something the Achievements show they have done? |
| Seniority | 20 | Do the scope and years asked for match the profile's `seniority` and the experience? |
| Industry | 15 | Is it one of the profile's `industries`, or adjacent? |

Be strict: 60 means a reasonable application, 80+ a strong match. Only credit what the Master Resume states; a requirement with no Achievement or skill behind it is a gap, not a guess. Score every candidate, including ones that look weak (the script applies `min_score`).

Write `data/search/<date>/scores.json`, keyed by candidate `key`:

```json
{"nvidia-jr2014555": {"score": 78, "summary": "one or two sentences on the fit",
  "interview_odds": "55-65%",
  "strengths": ["short, specific"], "gaps": ["short, specific"],
  "risks": ["short, specific"], "prep": ["short, specific"]}}
```

- `strengths`: each cites the concrete evidence from the Master Resume (employer, project or result), e.g. "Application Engineer at FTDI matches the customer-support duty", not just "C++".
- `gaps`: each names the JD requirement the Master Resume does not cover.
- `interview_odds`: an estimated range for getting past the interviews, as a percentage string. Base it on the fit and the risks, and on interview reports (interview.tw, PTT, Glassdoor) when you have them. It is a judgement, not a statistic.
- `risks`: anything that hurts the odds or the offer besides skills: the role is pitched below the candidate's level (overqualified), the salary is likely below the current level, the commute, the company's stability. Leave the list empty when there is none.
- `prep`: one to three concrete actions that would close the biggest gap before the interview, such as a weekend project with the company's public SDK or which topics to review.

For a large candidate list, score in batches of about 10 and keep each batch's JSON on disk as you go.

## 5. Write jobs and index

```
python scripts/search_jobs.py write data/search/<date>/candidates.json data/search/<date>/scores.json [overrides]
```

Writes `jobs/<key>.md` (frontmatter `url, status: new, score, fetched_at, …`, then Fit, Gaps and the JD) for each score at or above `min_score`, never overwriting an existing file or its `status`, and regenerates `jobs/INDEX.md` sorted by score with `ignored` jobs hidden. It writes nothing if any score is not an integer 0-100, and exits non-zero if a candidate has no score.

## 6. Company research (only with `research=N`)

Take the jobs written in step 5, highest score first, and pick the first N distinct companies. Run the `/research` skill (`.claude/skills/research/SKILL.md`) for each company. Pass the company name, so that every job of the company is written back. A company whose profile is still fresh costs almost nothing. Without `research=`, skip this step; the user can run `/research jobs/<key>.md` later.

## 7. Report

Answer in the user's language (Traditional Chinese if they wrote in Chinese). Say how many were fetched per source, how many survived the filter and how many were listed. Show the top five from `jobs/INDEX.md` as a table (score, interview odds, company, title, location, plus pay and trend for jobs that have them). Then, for each of the top three, give a short breakdown with headings for strengths (優勢), gaps (缺口), risks (風險) and, where it helps, prep (準備). Name any source that was blocked, skipped or failed. If step 6 ran, add each researched company's Trend and any `[company]` risks to its jobs' breakdowns. Suggest `/tailor jobs/<key>.md` for the best match and, if step 6 did not run, `/research jobs/<key>.md` for it.

Postings that score below `min_score` are not saved, so a later search fetches and scores them again. Lowering `min_score` later means searching again.
