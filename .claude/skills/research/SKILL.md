---
name: research
description: Research a company's pay, growth trend and work culture into a Company Profile in companies/, and add the results to its Job Postings. Use when the user runs /research with a job file or company name, asks how much a job pays, whether a company is growing or shrinking, or what it is like to work there.
---

# /research

Read `CONTEXT.md` and `docs/adr/0005-company-research.md` first. The input is one of:
- `jobs/<key>.md`: research that job's company, then write back to that job and every other job of the company.
- a company name or alias (`輝達`, `TSMC`): research the company, then write back to all its jobs.
- either of the above followed by `refresh`: research every section, whatever its `checked` date.

Answer in the user's language (Traditional Chinese if they wrote in Chinese). Profiles are written in Traditional Chinese with quotes in their original language.

## 1. Find or create the Company Profile

```
python scripts/companies.py find "<company name from the job's `company` or the argument>"
```

It prints the slug, or exits 1 if there is no profile. Try the Chinese and English names before creating one. A new profile is `companies/<slug>.md`, where the slug is the company's English name in lowercase with hyphens (`nvidia`, `mediatek`). A Taiwan branch or subsidiary (NVIDIA Taiwan, 輝達) goes into the parent's profile as an alias.

Then list the sections to research:

```
python scripts/companies.py stale <slug>
```

It prints `growth`, `culture` and/or `pay` for each section that is missing or older than its TTL. Research only those, unless the user said `refresh`. If none are printed, skip to step 3.

## 2. Research

Use WebSearch and WebFetch for public pages. Read pages that need a login or block scripts (Glassdoor, Dcard) through Claude in Chrome with the user's own login (read the `chrome-browser` skill first). If the browser is unavailable or the user is not logged in, skip that source and say so. Never try to get around a block (ADR 0003). Every piece of evidence needs a source (site and URL) and a date, so the reader can judge how old and how reliable it is. Prefer Taiwan sources for pay and culture; Trend is about the whole company.

### Trend (`growth`)
- Listed companies: monthly and annual revenue YoY from MOPS 公開資訊觀測站 (Taiwan) or the latest quarterly results (foreign listed).
- Layoffs, hiring freezes, expansion, new sites or funding in the last 12 months (news).
- The number of open roles or employees on 104's company page, as supporting evidence only.

Pick `growing`, `flat`, `shrinking` or `unknown`, backed by 2-3 dated, sourced points led by revenue and layoff or hiring news. Forum opinion only supports a label; it never sets it. Without enough evidence, say `unknown` rather than guess.

### Culture
Four fixed facets, each `正面`, `混合`, `負面` or `不明`, with 1-2 dated, sourced quotes:
- 工時／加班: hours, overtime, on-call, 責任制
- 主管與管理: managers, management style
- 升遷與考績: promotion and review system
- 工作彈性: WFH, flexible hours

Sources: PTT (Tech_Job, Salary boards), Dcard (工作板), Glassdoor, GoodJob 職場透明化運動, interview.tw. End with one sentence summing up.

### Pay
- **Posted**: the salary field of the company's 104 postings, monthly. "待遇面議" means at least NT$40,000/month and says nothing more.
- **Reported**: GoodJob, PTT, Glassdoor, Levels.fyi, interview.tw. Convert every report to annual total comp in NT$ (12-14 months of base plus bonus, profit sharing and stock; say what you assumed). Note the title, level and year of each report.

Write company-wide engineering pay as min / median / max with `n`, and mark a figure based on fewer than 3 reports as `僅供參考`.

## 3. Write the Company Profile

Overwrite the researched sections and keep the others. Set the `checked` date of each researched section to today.

```markdown
---
name: NVIDIA
aliases: [輝達, NVIDIA Taiwan]
trend: growing            # growing | flat | shrinking | unknown
checked: {growth: 2026-10-06, culture: 2026-10-06, pay: 2026-10-06}
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

## 薪資
- **公告**：104 職缺 NT$80k–150k/月（2 筆，2026-09）
- **回報（工程職，年薪 total comp）**：min 2.0M／中位數 3.1M／max 5.5M（n=7；GoodJob 4、PTT 3；台灣）
- 每筆：職稱、職級、年份、金額、來源
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
   ```
   Append company risks to the existing **Risks** list (create it if absent), each starting with `[company]`, e.g. `[company] Reported median pay is below your current pay`, `[company] Revenue down 18% YoY and layoffs in 2026-06`, `[company] PTT reports regular overtime`. On a later run, replace the old `[company]` items rather than adding more. Leave the Fit section otherwise untouched.
4. **Frontmatter.** Set the fields with the script. Never change `score`:
   ```
   python scripts/search_jobs.py set <key> company_profile=<slug> "pay=3.1M (n=4)" [interview_odds=40-50%]
   ```
   `pay` is short for the INDEX column: the reported median for the role with its `n`, else the posted range, else leave it unset. Change `interview_odds` only when the company findings really move it (e.g. a hiring freeze, interview reports that are much harder or easier than expected), and add a `[company]` risk saying why. The script rebuilds `jobs/INDEX.md`.

## 5. Report

Per company: the Trend with its main evidence, the four culture facets as one line each, the pay figures with `n`, and which jobs were updated (new `[company]` risks, changed odds). Name every source that was skipped (login, block) and every section left `unknown` or `不明`.
