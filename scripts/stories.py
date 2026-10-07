"""Story Bank in data/stories.yaml: STAR(+Reflection) interview stories built from Master Resume Achievements.

  validate   check the schema, that every cited Achievement exists in the master and is not do-not-use,
             and that every number in a story's situation/task/action/result appears in a cited Achievement
  status     print `missing`, `stale <ids>` (master Achievement ids not in built_from) or `ok`
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

from validate import _achievements, _schema_errors

STAR_FIELDS = ("situation", "task", "action", "result")  # reflection is the user's own words, not checked
THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    """Numbers in `text`, normalised so 1,700 matches 1700 and 03 matches 3."""
    found = set()
    for token in NUMBER.findall(THOUSANDS.sub("", text)):
        found.add(token if "." in token else str(int(token)))
    return found


def _entries(master: dict):
    for section in ("experience", "projects"):
        yield from master.get(section, [])


def _allowed_numbers(ach: dict, entry: dict) -> set[str]:
    """What a story may state about one Achievement: its text, metrics and its entry's period."""
    period = entry.get("period", {})
    parts = [ach["text"], *ach.get("metrics", []), period.get("start", ""), period.get("end", "")]
    return numbers(" ".join(parts))


def _check_stories(data: dict, master: dict) -> list[str]:
    errors = []
    by_id = {a["id"]: (a, e) for e in _entries(master) for a in e.get("achievements", [])}
    seen = set()
    for story in data["stories"]:
        label = f"story {story['id']}"
        if story["id"] in seen:
            errors.append(f"duplicate story id: {story['id']}")
        seen.add(story["id"])
        allowed: set[str] = set()
        for aid in story["achievements"]:
            if aid not in by_id:
                errors.append(f"{label}: achievement {aid} not found in master")
                continue
            ach, entry = by_id[aid]
            if "do-not-use" in ach.get("tags", []):
                errors.append(f"{label}: achievement {aid} is tagged do-not-use")
            allowed |= _allowed_numbers(ach, entry)
        for field in STAR_FIELDS:
            for number in sorted(numbers(story[field]) - allowed):
                errors.append(f"{label}: {field} states {number}, which no cited achievement has")
    return errors


def validate_stories(yaml_path: Path, schema_path: Path, master_path: Path) -> list[str]:
    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    errors = _schema_errors(data, schema_path)
    if errors:
        return errors
    master = yaml.safe_load(Path(master_path).read_text(encoding="utf-8"))
    return _check_stories(data, master)


def new_achievements(stories_path: Path, master_path: Path) -> list[str] | None:
    """Master Achievement ids the Story Bank was not built from, in master order; None if there is no bank."""
    if not Path(stories_path).is_file():
        return None
    data = yaml.safe_load(Path(stories_path).read_text(encoding="utf-8")) or {}
    built = set(data.get("built_from") or [])
    master = yaml.safe_load(Path(master_path).read_text(encoding="utf-8"))
    return [a["id"] for a in _achievements(master) if a["id"] not in built]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cmd", choices=["validate", "status"])
    parser.add_argument("--stories", type=Path, default=Path("data/stories.yaml"))
    parser.add_argument("--master", type=Path, default=Path("data/master.yaml"))
    parser.add_argument("--schema", type=Path, default=Path("schemas/stories.schema.json"))
    args = parser.parse_args()

    if args.cmd == "status":
        new = new_achievements(args.stories, args.master)
        print("missing" if new is None else f"stale {' '.join(new)}" if new else "ok")
        return 0
    errors = validate_stories(args.stories, args.schema, args.master)
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print(f"{args.stories}: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
