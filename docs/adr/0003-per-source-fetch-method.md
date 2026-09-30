# 3. Each Job Source declares its fetch method

Status: accepted (2026-09-30)

## Context
104 and Workday (NVIDIA) expose JSON endpoints; others (e.g. TSMC SuccessFactors) are JS-heavy pages. No single fetch strategy works for all.

## Decision
`config/sources.yaml` entries declare `method: api | fetch | browser`. `api`/`fetch` sources are handled by `scripts/fetch_jobs.py` adapters; `browser` sources are driven by the agent via Claude in Chrome. `/add-source` probes a new URL and picks the cheapest method that works.

## Consequences
Stable sources are fast and cheap; hard sources still work, just slower. New adapters are added only when a site family (Workday, SuccessFactors…) recurs.
