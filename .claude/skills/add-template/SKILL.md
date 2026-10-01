---
name: add-template
description: Turn a plain .docx CV into a tagged CV Template (docxtpl) in templates/. Use when the user runs /add-template or wants a new resume layout.
---

# /add-template

Convert a plain `.docx` CV into a CV Template. Read `CONTEXT.md`, `docs/adr/0004-docxtpl-templates.md` and `docs/cv-template-data.md` (the variables a template can use) first.

## 1. Inspect the source

Ask for the path if not given. Open it with python-docx and list each paragraph with its style, alignment, tab stops and runs, so you know which text is a heading, a repeated entry, or a bullet. A legacy `.doc` must first be saved as `.docx` (Word: `SaveAs2(path, 16)`).

## 2. Insert tags

Copy the file to `templates/<name>.docx` and edit the copy; never modify the user's original.

- Replace sample values with `{{ ... }}` variables from `docs/cv-template-data.md`.
- Turn one sample entry of each repeated section (experience, education, certifications, skills, bullets) into a loop. Put each `{%p for ... %}` / `{%p endfor %}` in its own paragraph around the entry, and wrap optional sections in `{%p if x %}`.
- Keep the original fonts, margins, tab stops and borders. Put each tag inside a single run, as Word splits runs on formatting changes and a tag split across runs will not render.
- Remove sections the data cannot fill (for example "Reason for leaving") and tell the user.

## 3. Verify

```
python scripts/render_resume.py data/master.yaml templates/<name>.docx output/sample
```

Check that the docx has no leftover `{{` or `{%`, that the PDF is produced (needs Word), and look at the PDF pages for layout problems. Fix and re-render until the layout is intact, then report the template path and anything dropped.
