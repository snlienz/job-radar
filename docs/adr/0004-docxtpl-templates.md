# 4. CV Templates are .docx files with docxtpl Jinja tags; output is docx + PDF

Status: accepted (2026-09-30)

## Context
The user switches CV layouts over time and needs HR-friendly Word output. Having the agent edit arbitrary .docx files each run gives unstable formatting.

## Decision
Templates in `templates/` contain Jinja tags (`{{ basics.name }}`, `{% for e in experience %}`) rendered by docxtpl in `scripts/render_resume.py`, then converted to PDF with docx2pdf (local Microsoft Word). `/add-template` converts a plain .docx into a tagged one once. Cover letters are out of scope for v1.

## Consequences
Rendering is reproducible and layout-preserving. PDF export requires Word on the machine (Windows/macOS).
