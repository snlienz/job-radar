# 8. Company Profiles record the company's direction, which never sets the Trend

Status: accepted (2026-10-07)

## Context
Trend (ADR 0005) rests on revenue YoY and layoff or hiring news. A private company publishes neither, so its Trend is often `unknown`. What is left is what its leaders say and do: who runs the company and who will next, where they say it is heading, and what it buys, builds or sells. That also answers a question the profile could not: whether the role being applied for sits at the core of the company's direction or on its edge. And it gives the user something to ask in the interview.

## Decision
- A Company Profile gets a `## 經營方向` section with its own `checked` date (`strategy`) and a 180-day TTL. A profile without it is stale for `strategy` only, so the next `/research` of the company adds it without redoing the others.
- It covers the whole leadership, not just the CEO: in many Taiwan companies the chairman or the family decides. A BU head belongs in the job's Department Notes.
- Four fixed facets, each with 1-3 dated, sourced points: leadership and governance (who runs it, tenure, family ownership and succession; any age, dated), stated direction (last 2 years), capital moves (acquisitions, new plants or businesses, funding, capital changes, divestments; last 3 years) and whether words match deeds (hiring, R&D, revenue mix). One overall label, `清楚且一致` / `清楚但未落實` / `模糊` / `不明`, and a summary sentence.
- What leaders say never sets the Trend; like forum opinion, it can only support a label. A gap between what they say and what the company does goes in the fourth facet.
- Sources follow ADR 0003: MOPS (annual report letter to shareholders, investor conference slides, material information) for listed companies; company news, media interviews and the MOEA company registry for all; 104 and the careers page for hiring; LinkedIn only in the user's Chrome when logged in.
- `/research` writes back to every job of the company a `策略關聯` line (核心 / 周邊 / 不明, with a reason) in its Company section, and for shortlisted jobs 2-3 questions to ask the interviewer. Four findings are `[company]` risks: 2 or more CEO or president changes in 2 years; undecided succession or a public fight over control; a direction that conflicts with the role (its business being closed or sold); a stated direction that the company's actions clearly contradict. Opinions about a leader's style are not a risk.
- The Company Gate shows the label and the job's `策略關聯`.

## Consequences
Private companies get a usable signal without letting press releases pass for results, and the user sees per job whether the company is investing in the work they would do. Strategy research costs a few more searches per company every 180 days. `策略關聯` is a judgement from the profile and the JD, written as text in the job; it adds no frontmatter field and never changes the Fit Score.
