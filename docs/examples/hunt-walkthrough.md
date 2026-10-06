# Example: a first `/hunt` session

繁體中文版：[hunt-walkthrough.zh-TW.md](hunt-walkthrough.zh-TW.md)

A real session, sanitized. It shows what you type, what `/hunt` does and what comes back, so you know what to expect on your first run.

**Sanitized:** the candidate, her employers, the hiring companies, job ids and every number about her are made up. Real 104 postings were used for the flow; company names are replaced with fictional ones. Score, odds and pay figures are illustrative.

**Starting point:** a cloned repo, `data/master.yaml` already built by `/scan`, an empty `keywords.include` in `config/profile.yaml`, no `config/private.yaml`.

---

## 1. Start

**You type**

```
/hunt https://www.104.com.tw/jobs/search/?keyword=senior+embedded+software&area=6001001000
```

You can also just type `/hunt` (continue where you are) or `/hunt search` (new search). `/hunt` only accepts `search` and `key=value` overrides, so a search URL is not used as the search itself; treat it as a hint for the keywords.

**What happens (step 0, setup)**
- `config/profile.yaml` exists and `data/master.yaml` exists.
- `keywords.include` is empty, so `/hunt` stops and asks which keywords to use. You answer in the chat; choose "write to profile" to keep them for next time.
- It warns, without stopping, that `config/private.yaml` is missing (pay cannot be compared with yours) and that Claude in Chrome is needed for 104.

> Tip: an include keyword is matched as a whole phrase in a title or JD, so `senior embedded software` keeps almost nothing. Single words (`embedded`, `firmware`) work better. `/search` accepts a one-run override: `keywords=embedded,firmware,driver,linux`.

## 2. Search

`stages` shows nothing waiting (no tailored, research, decide or new jobs), so `/hunt` goes to step 5 and runs `/search`.

1. The script fetch of 104 is refused (`BLOCKED ... HTTP 403`). This is normal; 104 often blocks scripts. `/hunt` does not work around it and switches to your Chrome (Claude in Chrome). If the extension is not connected it stops and tells you what to check; fix it and type `try again`.
2. In Chrome it reads the result page, then the JD of each embedded-looking job.
3. Hard filter: 12 postings in, 11 candidates out (1 had no include keyword).
4. Each candidate is scored 0-100 against your Master Resume. Jobs scoring 60 or more (7 here) are written to `jobs/<company>-<id>.md`, and `jobs/INDEX.md` is rebuilt.

## 3. Fit Gate (you decide)

**You see** a table, highest score first:

| # | Score | Odds | Company | Title | Summary | Biggest gap |
|---|---|---|---|---|---|---|
| 1 | 80 | 55-65% | Nimbus Cloud | Senior Embedded Software Engineer | Firmware, RTOS, Linux, C/C++; fits the candidate's firmware and embedded Linux background | No switching/routing protocol experience; posting is 5 months old |
| 2 | 76 | 55-65% | Lumen Devices | Embedded Software Engineer | Camera imaging firmware in C++ and embedded Linux | Pitched at 3-4 years: overqualified |
| 3 | 72 | 45-55% | Roboto Robotics | Senior Firmware & Embedded Engineer | Robotics firmware, real-time, vision sensors | No control-loop or robotics experience |
| ... | | | | | | |
| 6 | 64 | 35-45% | Mega Electronics | Embedded Systems Integration Engineer | Sensor firmware config, UART/I2C/SPI debugging | No PID/EKF tuning |

**You type** a number to shortlist it:

```
Add #1
```

`/hunt` sets the job to `shortlisted` (`python scripts/search_jobs.py status <key> shortlisted`) and moves on to research. Jobs you do not pick stay `new` and come back next time. Say "drop the rest" to set the others to `ignored`.

## 4. Research (automatic for shortlisted jobs)

`/research` writes a Company Profile in `companies/<slug>.md` and adds a `## Company` section, `[company]` risks, pay and department notes to the job file.

For a tiny company almost nothing public exists, and the profile says so instead of guessing:

- Trend: `unknown` (no revenue, funding or layoff news; 22 employees on 104)
- Culture, all five facets: `不明` (unknown)
- Pay: no engineering reports (n=0)
- Risk added: `[company] Only ~22 employees, stability cannot be judged`

## 5. Company Gate (you decide)

**You see** one row per researched job: score, odds, company, title, Trend, role pay, one line per culture facet, department notes and `[company]` risks. Then you choose for each job: `/tailor` it, drop it (`ignored`), or leave it.

You can also ask for a specific job by its number from the Fit Gate table at any time:

```
Evaluate #6
```

That shortlists it and runs the same research. A big company gives a much fuller picture:

- Trend: **growing** (revenue up 51% year over year in the latest month, with sources and dates)
- Hours: mixed, flexible start time, some teams report weekend overtime
- Management: mixed. Promotion: negative (2.5/5 on GoodJob). Flexibility: positive. Benefits: positive.
- Pay: company-level engineering reports, about NT$0.95-1.2M a year (n=4, marked "reference only")
- Department notes: `查無資料` (nothing found) for the robotics centre

## 6. Tailor

**You type**

```
/tailor #6
```

(A typo such as `/trailor` is not a command. The assistant asks whether you meant `/tailor` before running anything.)

`/tailor` produces `output/<company>-<id>/`:

| File | What it is |
|---|---|
| `resume.docx`, `resume.pdf` | the English Tailored Resume (PDF needs Word) |
| `tailored.yaml` | the data behind it; every bullet points to a Master Resume Achievement `id` |
| `changes.md` | what was selected, rephrased and dropped, and the **gaps** |

The validator checks that nothing was invented: all Highlight achievements present, no changed titles or dates, no skill missing from the Master Resume. Then the job is set to `tailored`.

**What to check by eye:** the summary (the only new free text) and the rephrased bullets. The gap list is the useful part: requirements the job asks for that your Master Resume cannot support. Add real experience through `/scan` (Gap Interview) and the next resume improves.

## 7. End of the run

`/hunt` closes with what changed and what the next run will do first. For this session:

- Statuses set: 1 job `shortlisted` and researched, 1 job `shortlisted` then `tailored`
- Companies researched: 2 (new files in `companies/`)
- Resumes made: 1
- Next `/hunt`: asks whether you applied to the tailored job, then returns to the Company Gate for the other shortlisted job, then the 5 `new` jobs still waiting at the Fit Gate.

---

## Things that went wrong, and what they mean

| What you see | Cause | What to do |
|---|---|---|
| `ModuleNotFoundError: yaml` (or `httpx`, `lxml`, `jsonschema`, `docxtpl`) | The Python environment is not the one with the project installed | Activate `.venv` and run `pip install -e ".[dev]"` before starting Claude Code |
| `BLOCKED 104 ... 403` | 104 refuses scripts | Install Claude in Chrome, sign in with the same Claude account, restart Chrome, then `try again` |
| "Browser extension is not connected" | Extension not running or not signed in | Same as above, or paste the job text into the chat |
| Almost no postings survive the filter | Include keyword is a long phrase | Use single words: `keywords=embedded,firmware` |
| Chinese file names look garbled in the Windows console | Console code page only | The files are fine (UTF-8); set `PYTHONIOENCODING=utf-8` to read them in the console |
| `config/private.yaml` missing | Not created yet | Copy `config/private.example.yaml` if you want pay compared with your own; it is gitignored |

## Where your data lives

`data/`, `jobs/`, `companies/`, `output/` and `config/profile.yaml` / `config/private.yaml` are gitignored. Nothing in this session is committed, so your resume, salary and research stay on your machine.
