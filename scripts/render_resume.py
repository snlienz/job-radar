"""Render a resume YAML (Master Resume shape) through a CV Template to resume.docx and resume.pdf."""
import argparse
import sys
from pathlib import Path

import yaml
from docxtpl import DocxTemplate

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _date(value: str) -> str:
    if value == "present":
        return "Present"
    year, _, month = value.partition("-")
    return f"{MONTHS[int(month) - 1]} {year}" if month else year


def _period(period: dict | None) -> str:
    if not period:
        return ""
    start = _date(period["start"])
    end = _date(period["end"]) if period.get("end") else ""
    return f"{start} – {end}" if end else start


def _skill_groups(skills: list[dict]) -> list[dict]:
    groups: dict[str, list[str]] = {}
    for s in skills:
        groups.setdefault(s.get("category") or "Other", []).append(s["name"])
    return [{"category": c, "names": ", ".join(n)} for c, n in groups.items()]


def _grouped_ids(job: dict) -> set:
    """Master area membership (ids); a tailored area holds its bullets itself."""
    return {aid for area in job.get("areas", []) for aid in area["achievements"] if isinstance(aid, str)}


def _areas(job: dict) -> list[dict]:
    """Work Areas with their bullets: a tailored area holds bullets, a master area holds ids."""
    by_id = {a["id"]: a for a in job.get("achievements", []) if "id" in a}
    areas = []
    for area in job.get("areas", []):
        items = [by_id.get(a) if isinstance(a, str) else a for a in area["achievements"]]
        bullets = [a["text"] for a in items if a and "do-not-use" not in a.get("tags", [])]
        if bullets:
            summary = area.get("summary")
            areas.append({"name": area["name"], "summary_suffix": f" – {summary}" if summary else "",
                          "bullets": bullets})
    return areas


def build_context(data: dict) -> dict:
    """Flatten a resume into the variables CV Templates use (see docs/cv-template-data.md)."""
    basics = data.get("basics", {})
    contact = [basics.get(k) for k in ("email", "phone", "location")] + list(basics.get("links", []))
    return {
        "basics": {**basics, "contact": " | ".join(c for c in contact if c)},
        "summary": basics.get("summary", ""),
        "highlights": [h["text"] for h in data.get("highlights", [])],
        "skills": _skill_groups(data.get("skills", [])),
        "experience": [
            {
                "company": job["company"],
                "location_suffix": f", {job['location']}" if job.get("location") else "",
                "title": job["title"],
                "period": _period(job.get("period")),
                "areas": _areas(job),
                "bullets": [
                    a["text"] for a in job.get("achievements", [])
                    if "do-not-use" not in a.get("tags", []) and a.get("id") not in _grouped_ids(job)
                ],
            }
            for job in data.get("experience", [])
        ],
        "education": [
            {
                "school": e["school"],
                "degree": e["degree"] + (f", {e['field']}" if e.get("field") else ""),
                "period": _period(e.get("period")),
            }
            for e in data.get("education", [])
        ],
        "certifications": [
            {"line": c["name"] + (f", {c['issuer']}" if c.get("issuer") else "")
                     + (f", {c['date']}" if c.get("date") else "")}
            for c in data.get("certifications", [])
        ],
        "languages": ", ".join(
            l["name"] + (f" ({l['level']})" if l.get("level") else "") for l in data.get("languages", [])
        ),
    }


def render_docx(data: dict, template: Path, out: Path) -> Path:
    doc = DocxTemplate(template)
    doc.render(build_context(data))
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


def render_pdf(docx_path: Path, pdf_path: Path) -> Path:
    from docx2pdf import convert  # needs Microsoft Word

    convert(str(docx_path), str(pdf_path))
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("resume", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--no-pdf", action="store_true", help="skip the Word PDF export")
    args = parser.parse_args()

    data = yaml.safe_load(args.resume.read_text(encoding="utf-8"))
    docx_path = render_docx(data, args.template, args.out_dir / "resume.docx")
    print(f"wrote {docx_path}")
    if args.no_pdf:
        return
    try:
        print(f"wrote {render_pdf(docx_path, args.out_dir / 'resume.pdf')}")
    except Exception as exc:  # Word missing or export failed; the docx is still usable
        print(f"PDF export failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
