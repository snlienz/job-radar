---
name: research
description: Research a company's pay, growth trend, work culture and direction (leadership, strategy) into a Company Profile in companies/, and add the results to its Job Postings. Use when the user runs /research with a job file, company name or posting URL, asks how much a job pays, whether a company is growing or shrinking, what it is like to work there, or where its leadership is taking it.
---

# /research

Read `CONTEXT.md`, `docs/adr/0005-company-research.md` and `docs/adr/0008-company-strategy.md` first. The input is one of:
- `jobs/<key>.md`: research that job's company, then write back to that job and every other job of the company.
- a company name or alias (`輝達`, `TSMC`): research the company, then write back to all its jobs.
- a posting URL (a careers page or 104 job page): run `python scripts/search_jobs.py lookup <url>`. If it prints a job file, carry on as for that job file. If not, read the page (WebFetch; if it is blocked or JS-rendered, read it in the browser as `/search` step 2 does) for the company, title, seniority (years asked for) and any posted pay. Research that company as for a company name. In step 4, there is no job file to write back to: work out the role pay and 策略關聯 for this posting all the same and give them in the report, then suggest `/search url=<url>` to score it and save it to `jobs/`, followed by `/research <company>`, which writes the fresh profile back to it without researching again.
- any of the above followed by `refresh`: research every section, whatever its `checked` date.

Answer in the user's language (Traditional Chinese if they wrote in Chinese). Profiles are written in Traditional Chinese with quotes in their original language.

**Cite every fact.** Every company fact, in the profile, the job's `## Company` section, a `[company]` risk, the report or any answer about the company, carries its source right after it as a link with the site and date: `（[interview.tw，2026-05](https://…)）`. A list of sources at the end does not replace this. When the date is unknown, write `日期不明`; when a source has no URL (a fact the user told you), say where it came from. A conclusion of your own (a Trend or culture label, 策略關聯, the skills a company probably wants) is marked `推測` and names the facts it rests on. Never state a company fact you have no source for.

## 1. Find or create the Company Profile

```
python scripts/companies.py find "<company name from the job's `company` or the argument>"
```

It prints the slug, or exits 1 if there is no profile. Try the Chinese and English names before creating one. A new profile is `companies/<slug>.md`, where the slug is the company's English name in lowercase with hyphens (`nvidia`, `mediatek`). A Taiwan branch or subsidiary (NVIDIA Taiwan, 輝達) goes into the parent's profile as an alias.

Then list the sections to research:

```
python scripts/companies.py stale <slug>
```

It prints `growth`, `culture`, `pay` and/or `strategy` for each section that is missing or older than its TTL. Research only those, unless the user said `refresh`. If none are printed, skip to step 3.

## 2. Research

Use WebSearch and WebFetch for public pages. Read pages that need a login or block scripts (Glassdoor, Dcard) through Claude in Chrome with the user's own login (read the `chrome-browser` skill first). If the browser is unavailable or the user is not logged in, skip that source and say so. Never try to get around a block (ADR 0003). Every piece of evidence needs a source (site and URL) and a date, so the reader can judge how old and how reliable it is. Prefer Taiwan sources for pay and culture; Trend is about the whole company.

### Trend (`growth`)
- Listed companies: monthly and annual revenue YoY from MOPS 公開資訊觀測站 (Taiwan) or the latest quarterly results (foreign listed).
- Layoffs, hiring freezes, expansion, new sites or funding in the last 12 months (news).
- The number of open roles or employees on 104's company page, as supporting evidence only.

Pick `growing`, `flat`, `shrinking` or `unknown`, backed by 2-3 dated, sourced points led by revenue and layoff or hiring news. Forum opinion only supports a label; it never sets it. Without enough evidence, say `unknown` rather than guess.

### Culture
Five fixed facets, each `正面`, `混合`, `負面` or `不明`, with 1-2 dated, sourced quotes:
- 工時／加班: hours, overtime, on-call, 責任制
- 主管與管理: managers, management style, and reports of workplace bullying (職場霸凌)
- 升遷與考績: promotion and review system
- 工作彈性: WFH, flexible hours
- 福利: year-end bonus, profit sharing, employee stock, insurance, leave, other benefits

Sources: PTT (Tech_Job, Salary boards), Dcard (工作板), Glassdoor, GoodJob 職場透明化運動, interview.tw, and Google (WebSearch) for anything else. End with one sentence summing up.

A profile written before the 福利 facet has no 福利 line. It is researched only when the culture section goes stale or the user says `refresh`; until then report it as `未研究`.

### Pay
- **Posted**: the salary field of the company's 104 postings, monthly. "待遇面議" means at least NT$40,000/month and says nothing more.
- **Reported**: GoodJob, PTT, Glassdoor, Levels.fyi, interview.tw. Convert every report to annual total comp in NT$ (12-14 months of base plus bonus, profit sharing and stock; say what you assumed). Note the title, level and year of each report.

Write company-wide engineering pay as min / median / max with `n`, and mark a figure based on fewer than 3 reports as `僅供參考`.

### 經營方向 (`strategy`)
The whole leadership, not just the CEO: in many Taiwan companies the chairman or the family decides. Four fixed facets, each with 1-3 dated, sourced points:
- 領導層與治理: who runs the company (chairman, president/CEO), background and tenure; family ownership and succession; changes in the last 2 years. Any age, dated.
- 策略方向: stated priorities and transformation, from the last 2 years only.
- 資本動作: acquisitions, new plants or businesses, funding, capital increases or reductions, divestments, from the last 3 years.
- 言行一致: whether the stated direction shows up in hiring (number and kind of openings), R&D investment or revenue mix.

Sources: for listed companies, MOPS (the annual report's 致股東報告書, investor conference slides, material information); for all, the company's news page, media interviews (經濟日報, 工商時報, 數位時代, 科技新報) and the MOEA company registry (directors, capital changes); the 104 company page and the careers page for hiring. LinkedIn (leadership changes, engineering headcount) only through Claude in Chrome when the user is logged in; otherwise skip it and say so.

Pick one label: `清楚且一致` (a clear direction the company acts on), `清楚但未落實` (clear words, little action), `模糊` or `不明` (not enough found). End with one sentence summing up. What leaders say never changes the Trend: it is a claim, not a result. Put a gap between words and deeds in 言行一致.

## 3. Write the Company Profile

Overwrite the researched sections and keep the others. Set the `checked` date of each researched section to today.

```markdown
---
name: NVIDIA
aliases: [輝達, NVIDIA Taiwan]
trend: growing            # growing | flat | shrinking | unknown
checked: {growth: 2026-10-06, culture: 2026-10-06, pay: 2026-10-06, strategy: 2026-10-06}
---

# NVIDIA

## 趨勢：成長
- 2026 Q2 營收 YoY +56%（NVIDIA 財報，2026-08-27，<url>）
- …

## 文化
總結：…
- **工時／加班：混合**：「…」（PTT Tech_Job，2026-05，<url>）
- **主管與管理：…**
- **升遷與考績：…**
- **工作彈性：…**
- **福利：…**

## 薪資
- **公告**：104 職缺 NT$80k–150k/月（2 筆，2026-09）
- **回報（工程職，年薪 total comp）**：min 2.0M／中位數 3.1M／max 5.5M（n=7；GoodJob 4、PTT 3；台灣）
- 每筆：職稱、職級、年份、金額、來源

## 經營方向：清楚且一致
總結：…
- **領導層與治理**：…（公司年報，2026-03，<url>）
- **策略方向**：…
- **資本動作**：…
- **言行一致**：…
```

## 4. Write back to the Job Postings

```
python scripts/companies.py jobs <slug>
```

It lists every non-ignored job file of the company. For each one (and for the job you were given, if not listed):

1. **Role pay.** Use reported pay for a similar title and level. With fewer than 3 such reports, use the company-wide engineering figures and label them `公司層級，非本職位`. Put the posted range of this posting first if it has one.
2. **Salary risk.** Read `config/private.yaml` (`salary.current_annual`, `salary.target_annual`). If the file is missing, skip this and tell the user to copy `config/private.example.yaml`. If the role's median is below `current_annual`, it is a risk; between current and target, it is a mild risk. Never write the user's salary into a job file or a profile; write only the comparison ("below your current pay").
3. **Body.** Add or replace a `## Company` section, just before `## Job description`:
   ```markdown
   ## Company

   [Company Profile](../companies/nvidia.md) · 趨勢：成長 ↑

   **Pay (this role):** 3.1M/yr median (n=4, 2026); posted NT$80k–150k/month

   **策略關聯：** 核心（推測）：公司正把資源投入 AI 資料中心（[NVIDIA 財報，2026-08-27](<url>)），這個職位做的是 GPU 系統軟體
   ```
   `策略關聯` is `核心`, `周邊` or `不明`, with one line on why, from the profile's 經營方向 and the JD.
   Append company risks to the existing **Risks** list (create it if absent), each starting with `[company]`, each with its source link, e.g. `[company] Reported median pay is below your current pay`, `[company] Revenue down 18% YoY and layoffs in 2026-06（[MOPS，2026-07](<url>)）`, `[company] PTT reports regular overtime（[PTT Tech_Job，2026-05](<url>)）`. On a later run, replace the old `[company]` items rather than adding more. Leave the Fit section otherwise untouched.

   **Direction.** Each of these is a `[company]` risk, with its source: 2 or more CEO or president changes in the last 2 years; succession undecided, or a public fight over control; a direction that conflicts with the role (its business being closed, sold or shrunk); a stated direction the company's actions clearly contradict (a proclaimed transformation while R&D openings keep shrinking). Opinions about a leader's style are not a risk; they stay in the profile.

   **Bullying.** One report of workplace bullying from the last 2 years that is specific (names the department or describes what a manager did) is a `[company]` risk, quoting it, e.g. `[company] Dcard 2026-03 reports a manager in the camera team publicly berating engineers (單一來源)`. Keep `(單一來源)` until two independent reports agree. A vague complaint stays in the 主管與管理 facet only.
4. **Department (shortlisted jobs only).** For a job with `status: shortlisted` and no `department` field (or with `refresh`), find the department, BU or team in its JD or title (e.g. `Camera BU`, `Mobile Computing`). If there is one, search Google (WebSearch), PTT and Dcard for the company with that department (心得, 加班, 主管, 面試) in the last 2 years. Add the findings under the job's `## Company` section, never to the Company Profile:
   ```markdown
   **部門傳聞（Camera BU）：**
   - 「…」（PTT Tech_Job，2026-04，<url>）
   ```
   Write `**部門傳聞（Camera BU）：** 查無資料` when nothing turns up, and `**部門傳聞：** JD 未載部門` when the JD names none. The bullying rule above applies here too. Department reports are sparse and go stale quickly, so they stay with the job. Skip this step for jobs that are not shortlisted (`/hunt` shortlists them at its Fit Gate).
5. **Interview questions (shortlisted jobs only).** Under the job's `## Company` section, add 2-3 questions to ask the interviewer, drawn from the 經營方向 and how the role fits it:
   ```markdown
   **可問面試官：**
   - 取得 ISO 26262 認證後，軟體團隊接下來會怎麼擴編？
   ```
   Replace them on a later run.
6. **Frontmatter.** Set the fields with the script. Never change `score`:
   ```
   python scripts/search_jobs.py set <key> company_profile=<slug> "pay=3.1M (n=4)" [department=<name or none>] [interview_odds=40-50%]
   ```
   Set `department` only for a job whose department was researched in item 4: its name, or `none` when the JD names none. `/hunt` reads it to tell a researched job from one still waiting.
   `pay` is short for the INDEX column: the reported median for the role with its `n`, else the posted range, else leave it unset. Change `interview_odds` only when the company findings really move it (e.g. a hiring freeze, interview reports that are much harder or easier than expected), and add a `[company]` risk saying why. The script rebuilds `jobs/INDEX.md`.

## 5. Report

Per company, every fact with its source link (see **Cite every fact**): the Trend with its main evidence, the five culture facets as one line each (`未研究` for a missing 福利), the pay figures with `n`, the 經營方向 label with its summary, and which jobs were updated (策略關聯, new `[company]` risks, changed odds). Name every source that was skipped (login, block) and every section left `unknown` or `不明`.
