"""Render data/master.yaml into a human-readable data/master.md."""
import argparse
from pathlib import Path

import yaml


def _period(p: dict | None) -> str:
    if not p:
        return ""
    return f"{p['start']} – {p.get('end', '')}".rstrip(" –")


def _achievements(items: list[dict]) -> list[str]:
    lines = []
    for a in items:
        flags = []
        if a.get("locked"):
            flags.append("locked")
        if a.get("confidence"):
            flags.append(a["confidence"])
        suffix = f" _({', '.join(flags)})_" if flags else ""
        lines.append(f"- **{a['id']}**: {a['text']}{suffix}")
        if a.get("metrics"):
            lines.append(f"  - metrics: {'; '.join(a['metrics'])}")
        if a.get("tags"):
            lines.append(f"  - tags: {', '.join(a['tags'])}")
        if a.get("conflict"):
            lines.append(f"  - ⚠ conflict: {a['conflict']}")
        for s in a["sources"]:
            lines.append(f"  - source: `{s['file']}` — “{s['quote']}”")
    return lines


def render(data: dict) -> str:
    b = data["basics"]
    out = [f"# {b['name']}", ""]
    contact = [b[k] for k in ("headline", "email", "phone", "location") if b.get(k)]
    if contact:
        out += [" · ".join(contact), ""]
    if b.get("summary"):
        out += [b["summary"], ""]

    out += ["## Experience", ""]
    for e in data["experience"]:
        out += [f"### {e['title']} — {e['company']} ({_period(e['period'])})", ""]
        by_id = {a["id"]: a for a in e["achievements"]}
        grouped = set()
        for area in e.get("areas", []):
            core = " _(core)_" if area.get("core") else ""
            summary = f" – {area['summary']}" if area.get("summary") else ""
            out += [f"#### {area['name']}{summary}{core}", ""]
            out += _achievements([by_id[i] for i in area["achievements"] if i in by_id]) + [""]
            grouped.update(area["achievements"])
        rest = [a for a in e["achievements"] if a["id"] not in grouped]
        if e.get("areas") and rest:
            out += ["#### Other", ""]
        out += _achievements(rest) + [""]

    if data.get("projects"):
        out += ["## Projects", ""]
        for p in data["projects"]:
            role = f" — {p['role']}" if p.get("role") else ""
            out += [f"### {p['name']}{role}", ""]
            out += _achievements(p["achievements"]) + [""]

    if data.get("skills"):
        out += ["## Skills", ""]
        for s in data["skills"]:
            meta = ", ".join(x for x in (s.get("category"), s.get("level")) if x)
            out.append(f"- {s['name']}" + (f" ({meta})" if meta else ""))
        out.append("")

    if data.get("education"):
        out += ["## Education", ""]
        for e in data["education"]:
            field = f", {e['field']}" if e.get("field") else ""
            out.append(f"- {e['degree']}{field} — {e['school']} {_period(e.get('period'))}".rstrip())
        out.append("")

    if data.get("certifications"):
        out += ["## Certifications", ""]
        for c in data["certifications"]:
            out.append(f"- {c['name']}" + (f" ({c['issuer']})" if c.get("issuer") else ""))
        out.append("")

    if data.get("languages"):
        out += ["## Languages", ""]
        for lang in data["languages"]:
            out.append(f"- {lang['name']}" + (f" ({lang['level']})" if lang.get("level") else ""))
        out.append("")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=Path("data/master.yaml"))
    parser.add_argument("--out", type=Path, default=Path("data/master.md"))
    args = parser.parse_args()
    data = yaml.safe_load(args.master.read_text(encoding="utf-8"))
    args.out.write_text(render(data), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
