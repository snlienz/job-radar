"""Company Profiles in companies/<slug>.md: find one by name or alias, check which sections are stale,
list the Job Postings that belong to it.

  find   <name>      print the slug whose name, slug or aliases match (exit 1 if none)
  stale  <slug>      print each section (growth, culture, pay) that is missing or past its TTL
  jobs   <slug>      print jobs/<key>.md for every non-ignored Job Posting of that company
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)
TTL_DAYS = {"growth": 90, "culture": 90, "pay": 180}  # docs/adr/0005-company-research.md
TRENDS = {"growing": "↑", "flat": "→", "shrinking": "↓", "unknown": "?"}


def _norm(name: str) -> str:
    return re.sub(r"[\W_]+", "", str(name).casefold())


def read_meta(path: Path) -> dict:
    match = FRONTMATTER.match(Path(path).read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    return yaml.safe_load(match.group(1)) or {}


def names(slug: str, meta: dict) -> set[str]:
    return {_norm(n) for n in [slug, meta.get("name", ""), *(meta.get("aliases") or [])] if _norm(n)}


def find(companies_dir: Path, name: str) -> str | None:
    """Slug of the Company Profile whose slug, name or aliases match `name` (case and punctuation ignored)."""
    wanted = _norm(name)
    for path in sorted(Path(companies_dir).glob("*.md")):
        if wanted in names(path.stem, read_meta(path)):
            return path.stem
    return None


def trend_arrow(companies_dir: Path, slug: str | None) -> str:
    path = Path(companies_dir) / f"{slug}.md"
    if not slug or not path.is_file():
        return ""
    return TRENDS.get(read_meta(path).get("trend"), "?")


def stale_sections(meta: dict, today: date) -> list[str]:
    checked = meta.get("checked") or {}
    stale = []
    for section, days in TTL_DAYS.items():
        when = checked.get(section)
        if isinstance(when, str):
            when = date.fromisoformat(when)
        if not when or (today - when).days > days:
            stale.append(section)
    return stale


def company_jobs(companies_dir: Path, jobs_dir: Path, slug: str) -> list[Path]:
    """Non-ignored job files linked to this profile (`company_profile`) or whose `company` matches its names."""
    known = names(slug, read_meta(Path(companies_dir) / f"{slug}.md"))
    found = []
    for path in sorted(Path(jobs_dir).glob("*.md")):
        if path.name == "INDEX.md":
            continue
        meta = read_meta(path)
        if meta.get("status") == "ignored":
            continue
        if meta.get("company_profile") == slug or _norm(meta.get("company", "")) in known:
            found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cmd", choices=("find", "stale", "jobs"))
    parser.add_argument("name", help="company name or alias (find), or profile slug")
    parser.add_argument("--companies", type=Path, default=Path("companies"))
    parser.add_argument("--jobs", type=Path, default=Path("jobs"))
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    if args.cmd == "find":
        slug = find(args.companies, args.name)
        if slug:
            print(slug)
        return 0 if slug else 1
    path = args.companies / f"{args.name}.md"
    if not path.is_file():
        print(f"ERROR no Company Profile {path}", file=sys.stderr)
        return 1
    if args.cmd == "stale":
        for section in stale_sections(read_meta(path), args.today):
            print(section)
    else:
        for job in company_jobs(args.companies, args.jobs, args.name):
            print(job.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
