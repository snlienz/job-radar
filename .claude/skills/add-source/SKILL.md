---
name: add-source
description: Add a company careers site to config/sources.yaml, detecting the right fetch method (api, fetch or browser). Use when the user runs /add-source <url> or wants /search to cover another company.
---

# /add-source

Read `docs/adr/0003-per-source-fetch-method.md` first. Ask for the careers-page URL if not given (the page that lists or searches jobs, not the company homepage).

## 1. Probe and add

```
python scripts/add_source.py <url> [--name <name>]
```

It picks the cheapest method that works: `api` for a platform with an adapter in `scripts/fetch_jobs.py` (Workday, 104), `fetch` for static HTML with job links, otherwise `browser` (scripted access refused, or the page is built by JavaScript). It makes one test fetch with the Search Profile, falls back to `browser` if that fails, and appends the entry to `config/sources.yaml` without touching the rest of the file. It refuses a source whose name or URL is already there. Use `--dry-run` to see the result without writing.

## 2. Confirm a browser source

The script cannot test a `browser` source. Open the URL with Claude in Chrome (read the `chrome-browser` skill first) and check that you can see job listings and open one posting's full description. If it needs a login, or shows no jobs, tell the user and remove the entry rather than leaving a source that cannot work.

## 3. Report

Say the name, method and why, and the result of the test fetch. If the script printed a `suggest:` line (a platform that has no adapter), tell the user and offer to write the adapter in `scripts/fetch_jobs.py` if they expect more sites on that platform; do not write it unasked.
