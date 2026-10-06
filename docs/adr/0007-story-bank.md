# 7. A job-independent Story Bank built from cited Achievements

Status: accepted (2026-10-06)

## Context
The repo helps up to the application but not with the interview. A good behavioral answer (STAR plus a reflection) needs the same facts the Master Resume already holds: Achievements with metrics and original-language quotes. Tools that build stories from a hand-written CV have to guard against invented numbers; here every story can rest on Achievements that already cite their sources.

## Decision
- A `/prep` skill builds `data/stories.yaml` (gitignored with the rest of `data/`), 5-10 English STAR(+Reflection) stories covering common behavioral themes. It reads no job or company: the stories are the user's past, the same for every interview.
- Each story cites the Achievement ids it draws on. Situation, task, action and result use only facts from those Achievements; `scripts/stories.py validate` rejects a dangling or `do-not-use` id, and any number not found in a cited Achievement's text, metrics or entry period. The reflection is the user's own words and is not checked.
- Reflections and missing context are asked of the user. A new fact goes into the Master Resume first, only once the user confirms it, so a story never knows more than the master.
- The bank records the Achievement ids it was built from (`built_from`). It is stale when the master has an id not in that list; edited text or removed ids do not make it stale. `/prep` with nothing new changes nothing.
- No new Hunt step, status or stage. `/hunt` step 0 and the end of a `/scan` that added Achievements only mention a missing or stale bank.

## Consequences
Stories change only when a scan brings new Achievements, so the user can rehearse them without them drifting. Matching numbers is a lexical check: a story that writes "70,000" for a metric "70K" fails and has to use the master's form, and a story can still misstate a fact without a number; the rule in the skill covers those. Per-job interview prep (likely questions for one JD) is left for later and can be done by hand from the job file and the bank.
