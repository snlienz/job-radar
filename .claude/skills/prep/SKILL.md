---
name: prep
description: Build or update the Story Bank data/stories.yaml, reusable STAR+Reflection interview stories drawn from the Master Resume's Achievements, asking the user for reflections and missing context. Use when the user runs /prep, wants to prepare for behavioral interviews, or /hunt or /scan says the Story Bank is missing or stale.
---

# /prep

Build the Story Bank `data/stories.yaml`. Read `CONTEXT.md` and `docs/adr/0007-story-bank.md` first. The schema is `schemas/stories.schema.json`. The Story Bank is about the user's past, not any job: it never reads `jobs/` or `companies/`.

Talk in the user's language (Traditional Chinese if they wrote in Chinese); the stories are English, like the Master Resume.

## 1. What to do

```
python scripts/stories.py status
```

- `missing`: build the bank (step 2).
- `stale <ids>`: the master has Achievements the bank was not built from. Read only those Achievements and decide, for each, whether it strengthens an existing story (add its id to that story's `achievements` and work its facts in) or, with related new ones, makes a new story. Leave the other stories as they are.
- `ok`: say the bank is current and stop. Do not rewrite or reorder stories. Change a story only when the user asks for it by name.

## 2. Build

Read `data/master.yaml` (all of it). Never read `data/raw/`; the Master Resume is the only source of facts.

Group related Achievements into 5-10 stories. Aim to cover these themes, one story can cover several:
- biggest technical challenge
- conflict or disagreement
- failure or mistake
- leadership or ownership without authority
- cross-team delivery
- ambiguity or a decision with incomplete data
- impact measured with data

Prefer Achievements with metrics and `confidence: high`, and the user's `highlight` ones. Skip any tagged `do-not-use`. A theme the master cannot support is left out and named in the report, not forced.

Each story has `id` (kebab-case), `title`, `themes`, `questions` (2-3 sample questions it answers), `achievements` (ids it draws on), and `situation`, `task`, `action`, `result`:
- **Never invent.** Situation, task, action and result use only facts from the cited Achievements' `text` and `metrics` and their entry's company, title and period. Every number must appear in a cited Achievement or its entry's period; the validator rejects any other. Do not upgrade "contributed to" into "led", or add team size, motive or conflict that no Achievement states.
- Keep each part to one to three sentences, first person, spoken style.
- What a good answer needs but the master does not say (who disagreed, why it was hard, what went wrong) goes into `open_questions`, not the story.

Set `built_from` to every Achievement id in the master, including the ones not used, so they do not count as new next time.

## 3. Interview

Ask the user, at most ~8 questions at a time, grouped by story:
- `reflection` for each story: what they learned or would do differently. Write their answer, lightly edited into English; never write one for them. With no answer, leave `reflection` out.
- the story's `open_questions`.

An answer that adds a fact (a metric, scope, team size, a conflict) belongs in the Master Resume first. Show the change to `data/master.yaml` and make it only once the user confirms; then follow `/scan` rules (`confidence: high`, never touch `locked`) and run `python scripts/validate.py data/master.yaml`. A fact added to an Achievement can then go into its story. Add any new Achievement id to `built_from`. Remove an open question once it is answered.

## 4. Validate

```
python scripts/stories.py validate
```

It checks the schema, that every cited Achievement exists in the master and is not `do-not-use`, and that every number in situation, task, action and result appears in a cited Achievement. Fix the story, never the validator or the master, and rerun until it passes.

## Report

List the stories (title, themes, cited ids), which themes have no story, and the open questions left.
