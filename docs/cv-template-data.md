# CV Template data shape

`scripts/render_resume.py` turns a resume YAML (same shape as `data/master.yaml`, see `schemas/master.schema.json`; a Tailored Resume, `schemas/tailored.schema.json`, renders too) into the variables below with `build_context()`, then renders the template with docxtpl. Achievements tagged `do-not-use` are dropped.

Use paragraph-level tags (`{%p if x %}`, `{%p for x in y %}`, `{%p endif %}`, `{%p endfor %}`), each alone in its own paragraph, so the tag paragraphs disappear from the output.

| Variable | Type | Notes |
|---|---|---|
| `basics.name`, `basics.headline`, `basics.email`, `basics.phone`, `basics.location`, `basics.links` | string / list | raw fields; may be missing |
| `basics.contact` | string | email, phone, location and links joined with ` \| ` |
| `summary` | string | `basics.summary`, empty if unset |
| `highlights` | list of strings | Key Achievements bullets (tailored `highlights[].text`), empty for a master |
| `skills` | list | `category`, `names` (comma-joined), grouped by category |
| `experience` | list | `company`, `location_suffix` (`", City"` or empty), `title`, `period`, `bullets` (list of strings) |
| `education` | list | `school`, `degree` (with field appended), `period` |
| `certifications` | list | `line` (name, issuer, date joined with commas) |
| `languages` | string | `English (Fluent), Chinese (Native)`, empty if none |

Periods are formatted like `Mar 2019 – Present`, `2014 – Jun 2018`.

Do not use `.items` as a variable name: it resolves to the dict method.
