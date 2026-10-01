"""Validate a Master Resume (schema + provenance) or, with --master, a Tailored Resume."""
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from extract import TEXT_SUFFIXES, read_text_file


def _achievements(data: dict):
    for section in ("experience", "projects"):
        for entry in data.get(section, []):
            yield from entry.get("achievements", [])


def _normalize(text: str) -> str:
    """Collapse whitespace runs: extraction may change line breaks."""
    return re.sub(r"\s+", " ", text).strip()


def _source_text(rel: str, raw_dir: Path, extracted_dir: Path) -> str | None:
    extracted = extracted_dir / (rel + ".txt")
    if extracted.is_file():
        return extracted.read_text(encoding="utf-8")
    raw = raw_dir / rel
    if raw.suffix.lower() in TEXT_SUFFIXES:
        return read_text_file(raw)
    return None


def _check_sources(owner: str, sources: list[dict], raw_dir: Path, extracted_dir: Path, texts: dict) -> list[str]:
    """Each source file exists in raw_dir and its quote appears verbatim in the extracted text."""
    errors = []
    for source in sources:
        rel = source["file"]
        if not (raw_dir / rel).is_file():
            errors.append(f"{owner}: source file not found in raw dir: {rel}")
            continue
        if rel not in texts:
            text = _source_text(rel, raw_dir, extracted_dir)
            texts[rel] = None if text is None else _normalize(text)
        if texts[rel] is None:
            errors.append(f"{owner}: no extracted text for {rel} (run scripts/extract.py), cannot check quote")
        elif _normalize(source["quote"]) not in texts[rel]:
            errors.append(f"{owner}: quote not found verbatim in {rel}: {source['quote'][:40]!r}")
    return errors


def _check_areas(data: dict, raw_dir: Path, extracted_dir: Path, texts: dict) -> list[str]:
    """Work Areas group an entry's own Achievements, each into at most one area."""
    errors = []
    for entry in data.get("experience", []):
        owned = {a["id"]: a for a in entry["achievements"]}
        grouped: dict[str, str] = {}
        for area in entry.get("areas", []):
            label = f"area {entry['id']}/{area['id']}"
            errors += _check_sources(label, area.get("sources", []), raw_dir, extracted_dir, texts)
            for aid in area["achievements"]:
                if aid not in owned:
                    errors.append(f"{label}: achievement {aid} not found in this entry")
                elif "highlight" in owned[aid].get("tags", []):
                    errors.append(f"{label}: achievement {aid} is tagged highlight and cannot be in an area")
                elif aid in grouped:
                    errors.append(f"{label}: achievement {aid} is already in area {grouped[aid]}")
                grouped.setdefault(aid, area["id"])
    return errors


def _check_provenance(data: dict, raw_dir: Path, extracted_dir: Path) -> list[str]:
    errors = []
    seen = set()
    texts: dict[str, str | None] = {}
    for ach in _achievements(data):
        if ach["id"] in seen:
            errors.append(f"duplicate achievement id: {ach['id']}")
        seen.add(ach["id"])
        errors += _check_sources(f"achievement {ach['id']}", ach.get("sources", []), raw_dir, extracted_dir, texts)
    errors += _check_areas(data, raw_dir, extracted_dir, texts)
    for skill in data.get("skills", []):
        for ref in skill.get("evidence", []):
            if ref not in seen:
                errors.append(f"skill {skill['name']}: evidence id not found: {ref}")
    return errors


def _schema_errors(data: dict, schema_path: Path) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(data)
    ]


def validate_file(
    yaml_path: Path, schema_path: Path, raw_dir: Path, extracted_dir: Path
) -> list[str]:
    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    errors = _schema_errors(data, schema_path)
    if errors:  # provenance checks assume a structurally valid file
        return errors
    return _check_provenance(data, Path(raw_dir), Path(extracted_dir))


FREE_BASICS = {"headline", "summary"}  # the only basics fields tailoring may rewrite


def _check_entries(section: str, label: str, entries: list[dict], master: dict, seen: set) -> list[str]:
    """Check each tailored experience/project entry and its bullets against the master."""
    errors = []
    master_entries = {e["id"]: e for e in master.get(section, [])}
    for entry in entries:
        owner = master_entries.get(entry["id"])
        if owner is None:
            errors.append(f"{label} id not found in master: {entry['id']}")
            continue
        for field in ("company", "title", "name", "role", "location", "period"):
            if field in entry and entry[field] != owner.get(field):
                errors.append(f"{label} {entry['id']}: {field} differs from master")
        owned = {a["id"]: a for a in owner["achievements"]}
        errors += _check_entry_areas(label, entry, owner)
        bullets = entry["achievements"] + [b for area in entry.get("areas", []) for b in area["achievements"]]
        for bullet in bullets:
            sid = bullet["source_id"]
            if sid not in owned:
                where = "another entry" if sid in _all_ids(master) else "master"
                errors.append(f"{label} {entry['id']}: source_id {sid} not found in this entry ({where})")
            elif "do-not-use" in owned[sid].get("tags", []):
                errors.append(f"{label} {entry['id']}: source_id {sid} is tagged do-not-use")
            if sid in seen:
                errors.append(f"source_id {sid} used twice")
            seen.add(sid)
    return errors


def _check_entry_areas(label: str, entry: dict, owner: dict) -> list[str]:
    """Bullets of a master Work Area sit in that area; every core area is present."""
    errors = []
    where = f"{label} {entry['id']}"
    areas = {a["id"]: a for a in owner.get("areas", [])}
    area_of = {aid: a["id"] for a in owner.get("areas", []) for aid in a["achievements"]}
    used = set()
    for area in entry.get("areas", []):
        master_area = areas.get(area["id"])
        if master_area is None:
            errors.append(f"{where}: area {area['id']} not found in master")
            continue
        used.add(area["id"])
        for field in ("name", "summary"):
            if area.get(field) != master_area.get(field):
                errors.append(f"{where}: area {area['id']} {field} differs from master")
        for bullet in area["achievements"]:
            if area_of.get(bullet["source_id"]) != area["id"]:
                errors.append(f"{where}: source_id {bullet['source_id']} is not in area {area['id']}")
    for bullet in entry["achievements"]:
        if bullet["source_id"] in area_of:
            errors.append(f"{where}: source_id {bullet['source_id']} belongs in area {area_of[bullet['source_id']]}")
    for area in areas.values():
        if area.get("core") and area["id"] not in used:
            errors.append(f"{where}: core area {area['id']} is missing")
    return errors


def _all_ids(master: dict) -> set:
    return {a["id"] for a in _achievements(master)}


def _check_highlights(bullets: list[dict], master: dict, seen: set) -> list[str]:
    """Highlights may cite any master Achievement, and must include every one tagged `highlight`."""
    errors = []
    by_id = {a["id"]: a for a in _achievements(master)}
    for bullet in bullets:
        sid = bullet["source_id"]
        if sid not in by_id:
            errors.append(f"highlights: source_id {sid} not found in master")
        elif "do-not-use" in by_id[sid].get("tags", []):
            errors.append(f"highlights: source_id {sid} is tagged do-not-use")
        if sid in seen:
            errors.append(f"source_id {sid} used twice")
        seen.add(sid)
    used = {b["source_id"] for b in bullets}
    for aid, ach in by_id.items():
        if "highlight" in ach.get("tags", []) and aid not in used:
            errors.append(f"highlights: {aid} is tagged highlight in master but missing from highlights")
    return errors


def _check_against_master(data: dict, master: dict) -> list[str]:
    errors = []
    for key, value in data["basics"].items():
        if key not in FREE_BASICS and value != master["basics"].get(key):
            errors.append(f"basics: {key} differs from master")
    seen: set = set()
    errors += _check_highlights(data.get("highlights", []), master, seen)
    errors += _check_entries("experience", "experience", data["experience"], master, seen)
    present = {e["id"] for e in data["experience"]}
    for entry in master.get("experience", []):
        if entry["id"] not in present and any(a.get("core") for a in entry.get("areas", [])):
            errors.append(f"experience {entry['id']}: has core areas but is missing")
    errors += _check_entries("projects", "project", data.get("projects", []), master, seen)
    master_skills = {s["name"].casefold() for s in master.get("skills", [])}
    for skill in data.get("skills", []):
        if skill["name"].casefold() not in master_skills:
            errors.append(f"skill not in master: {skill['name']}")
    for section in ("education", "certifications", "languages"):
        for item in data.get(section, []):
            if item not in master.get(section, []):
                label = item.get("school") or item["name"]
                errors.append(f"{section}: entry not in master: {label}")
    return errors


def validate_tailored(yaml_path: Path, schema_path: Path, master_path: Path) -> list[str]:
    """A Tailored Resume may select and rephrase, but every fact must trace to the master."""
    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    errors = _schema_errors(data, schema_path)
    if errors:
        return errors
    master = yaml.safe_load(Path(master_path).read_text(encoding="utf-8"))
    return _check_against_master(data, master)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument(
        "--master", type=Path, help="validate yaml_path as a Tailored Resume against this Master Resume"
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--extracted", type=Path, default=Path("data/extracted"))
    args = parser.parse_args()

    if args.master:
        schema = args.schema or Path("schemas/tailored.schema.json")
        errors = validate_tailored(args.yaml_path, schema, args.master)
    else:
        schema = args.schema or Path("schemas/master.schema.json")
        errors = validate_file(args.yaml_path, schema, args.raw, args.extracted)
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print(f"{args.yaml_path}: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
