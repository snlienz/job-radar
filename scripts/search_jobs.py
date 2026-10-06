"""Filter fetched Job Postings, then write scored ones to jobs/ and rebuild jobs/INDEX.md.

  filter  postings.json --out candidates.json [overrides]   hard filter + dedupe (+ `key` per posting)
  write   candidates.json scores.json [overrides]           jobs/<key>.md for scores >= min_score
  index                                                     regenerate jobs/INDEX.md only
  status  <key or jobs/<key>.md> <status>                   set a Job Posting's status, then reindex
  set     <key or jobs/<key>.md> field=value ...            set frontmatter fields written by /research
                                                            (pay, company_profile, interview_odds), then reindex
  lookup  <url>                                             print jobs/<key>.md for that posting URL (exit 1 if none)
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from companies import trend_arrow
from search_profile import load_profile

CITY_ALIASES = {  # profile names are English; postings are often Chinese
    "taipei": ["台北", "臺北"], "new taipei": ["新北"], "hsinchu": ["新竹"], "taichung": ["台中", "臺中"],
    "tainan": ["台南", "臺南"], "kaohsiung": ["高雄"], "taoyuan": ["桃園"],
}
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.S)
FIXED_FIELDS = {"score", "url"}  # the Fit Score is never rescored; url is the dedupe key
STATUSES = ("new","shortlisted", "tailored", "applied", "interview", "rejected", "offer", "ignored")


def slug(text: str) -> str:
    return re.sub(r"[\W_]+", "-", text.casefold()).strip("-") or "x"


def posting_key(posting: dict) -> str:
    return f"{slug(posting['company'])}-{slug(str(posting['id']))}"


def normalize_url(url: str) -> str:
    return url.split("#")[0].rstrip("/")


# --- job files ---------------------------------------------------------------------------------

def read_job(path: Path) -> tuple[dict, str]:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    return yaml.safe_load(match.group(1)) or {}, match.group(2)


def known_jobs(jobs_dir: Path) -> dict[str, dict]:
    """url -> frontmatter for every job file (any status, including ignored)."""
    jobs = {}
    for path in sorted(Path(jobs_dir).glob("*.md")):
        if path.name == "INDEX.md":
            continue
        meta, _ = read_job(path)
        if meta.get("url"):
            jobs[normalize_url(meta["url"])] = {**meta, "file": path.name}
    return jobs


def find_job(jobs_dir: Path, url: str) -> Path | None:
    """The job file whose `url` is this URL (ignoring a trailing slash or #fragment), any status."""
    job = known_jobs(jobs_dir).get(normalize_url(url))
    return Path(jobs_dir) / job["file"] if job else None


def set_fields(jobs_dir: Path, job: str, fields: dict[str, str]) -> Path:
    """Rewrite only the given top-level lines of a job file's frontmatter, then rebuild the index."""
    if fields.get("status", STATUSES[0]) not in STATUSES:
        raise ValueError(f"unknown status {fields['status']!r}; expected one of {', '.join(STATUSES)}")
    path = Path(jobs_dir) / f"{Path(job).stem}.md"
    if not path.is_file():
        raise FileNotFoundError(f"no job file {path}")
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    header = match.group(1)
    for key, value in fields.items():
        if not re.fullmatch(r"[a-z_]+", key):
            raise ValueError(f"bad field name {key!r}")
        if key in FIXED_FIELDS:
            raise ValueError(f"{key} is fixed once a job is written")
        line = yaml.safe_dump({key: value}, allow_unicode=True, width=1000).strip()
        header, n = re.subn(rf"^{key}:.*$", lambda _: line, header, count=1, flags=re.M)
        if not n:
            header += f"\n{line}"
    path.write_text(f"---\n{header}\n---\n{text[match.start(2):]}", encoding="utf-8")
    rebuild_index(jobs_dir)
    return path


def set_status(jobs_dir: Path, job: str, status: str) -> Path:
    return set_fields(jobs_dir, job, {"status": status})


# --- hard filter -------------------------------------------------------------------------------

def _location_terms(locations: list[str]) -> list[str]:
    terms = []
    for loc in locations:
        terms.append(loc.casefold())
        terms += CITY_ALIASES.get(loc.casefold(), [])
    return terms


def drop_reason(posting: dict, profile: dict) -> str | None:
    haystack = f"{posting['title']}\n{posting.get('jd_text', '')}".casefold()
    if profile["include"] and not any(k.casefold() in haystack for k in profile["include"]):
        return "no include keyword in title or JD"
    for word in profile["exclude"]:  # title only: JDs say "intern or full time", "work with sales"
        if word.casefold() in posting["title"].casefold():
            return f"exclude keyword: {word}"
    if profile["locations"]:
        location = posting.get("location", "").casefold()
        # a posting with no stated location is kept for scoring rather than silently lost
        if location and not any(t in location for t in _location_terms(profile["locations"])):
            return f"location not wanted: {posting['location']}"
    return None


def filter_postings(postings: list[dict], profile: dict, jobs_dir: Path) -> tuple[list[dict], list[dict]]:
    known = known_jobs(jobs_dir)
    keep, dropped, seen = [], [], set()
    for posting in postings:
        url = normalize_url(posting["url"])
        reason = None
        if url in seen:
            reason = "duplicate in this run"
        elif url in known:
            reason = "ignored" if known[url].get("status") == "ignored" else f"already in jobs/ ({known[url]['file']})"
        else:
            reason = drop_reason(posting, profile)
        seen.add(url)
        if reason:
            dropped.append({"key": posting_key(posting), "title": posting["title"], "reason": reason})
        else:
            keep.append({**posting, "key": posting_key(posting)})
    return keep, dropped


# --- write + index -----------------------------------------------------------------------------

def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items) if items else "- none"


def write_jobs(candidates: list[dict], scores: dict[str, dict], jobs_dir: Path, min_score: int, now: str) -> dict:
    """Write jobs/<key>.md for each scored candidate >= min_score; never overwrite an existing file."""
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    known = known_jobs(jobs_dir)
    result = {"written": [], "below_min": [], "unscored": [], "skipped": []}
    for posting in candidates:  # reject bad scores before writing anything
        score = scores.get(posting["key"], {}).get("score", 0)
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            raise ValueError(f"{posting['key']}: score must be an integer 0-100, got {score!r}")
    for posting in candidates:
        key = posting["key"]
        entry = scores.get(key)
        if entry is None:
            result["unscored"].append(key)
            continue
        score = entry["score"]
        if score < min_score:
            result["below_min"].append(key)
            continue
        path = jobs_dir / f"{key}.md"
        if normalize_url(posting["url"]) in known or path.exists():
            result["skipped"].append(key)
            continue
        meta = {
            "company": posting["company"], "title": posting["title"], "location": posting.get("location", ""),
            "url": posting["url"], "status": "new", "score": score, "fetched_at": now,
            "posted_at": posting.get("posted_at"),
        }
        odds = entry.get("interview_odds")
        if odds:
            meta["interview_odds"] = odds
        fit = [entry.get("summary", "")]
        if odds:
            fit.append(f"**Interview odds:** {odds}")
        fit += [f"**Strengths**\n{_bullets(entry.get('strengths', []))}",
                f"**Gaps**\n{_bullets(entry.get('gaps', []))}"]
        for label, field in (("Risks", "risks"), ("Prep", "prep")):  # optional sections
            if entry.get(field):
                fit.append(f"**{label}**\n{_bullets(entry[field])}")
        body = (
            f"# {posting['title']} — {posting['company']}\n\n"
            f"## Fit ({score}/100)\n\n" + "\n\n".join(fit) + "\n\n"
            f"## Job description\n\n{posting.get('jd_text', '').strip()}\n"
        )
        header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        path.write_text(f"---\n{header}\n---\n\n{body}", encoding="utf-8")
        result["written"].append(key)
    rebuild_index(jobs_dir)
    return result


def rebuild_index(jobs_dir: Path, companies_dir: Path | None = None) -> Path:
    """jobs/INDEX.md sorted by score. Pay comes from the job's `pay`, Trend from its Company Profile."""
    jobs_dir = Path(jobs_dir)
    companies_dir = Path(companies_dir) if companies_dir else jobs_dir.parent / "companies"
    rows = []
    for path in sorted(jobs_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        meta, _ = read_job(path)
        if meta.get("status") != "ignored":
            rows.append((meta.get("score") or 0, path.name, meta))
    rows.sort(key=lambda r: (-r[0], r[1]))
    lines = ["# Job Postings", "", "| Score | Odds | Pay | Trend | Status | Company | Title | Location | Posted |",
             "|---|---|---|---|---|---|---|---|---|"]
    for score, name, meta in rows:
        cells = [str(score), str(meta.get("interview_odds") or ""), str(meta.get("pay") or ""),
                 trend_arrow(companies_dir, meta.get("company_profile")), meta.get("status", ""),
                 meta.get("company", ""), f"[{meta.get('title', '')}]({name})",
                 meta.get("location", ""), str(meta.get("posted_at") or "")]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    index = jobs_dir / "INDEX.md"
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    positionals = {"filter": ["postings"], "write": ["candidates", "scores"], "index": [], "status": [], "set": [],
                   "lookup": []}
    for name, names in positionals.items():
        p = sub.add_parser(name)
        for arg in names:
            p.add_argument(arg, type=Path)
        p.add_argument("--jobs", type=Path, default=Path("jobs"))
        if name == "filter":
            p.add_argument("--out", type=Path, required=True)
        if name == "status":
            p.add_argument("job", help="job key or jobs/<key>.md")
            p.add_argument("status", choices=STATUSES)
        if name == "set":
            p.add_argument("job", help="job key or jobs/<key>.md")
            p.add_argument("fields", nargs="+", help="field=value")
        if name == "lookup":
            p.add_argument("url")
        if name not in ("index", "status", "set", "lookup"):
            p.add_argument("--profile", type=Path, default=Path("config/profile.yaml"))
            p.add_argument("overrides", nargs="*")
    args = parser.parse_args()

    if args.cmd == "index":
        print(f"wrote {rebuild_index(args.jobs)}")
        return 0
    if args.cmd == "status":
        try:
            path = set_status(args.jobs, args.job, args.status)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        print(f"{path}: status {args.status}; index rebuilt")
        return 0
    if args.cmd == "set":
        fields = dict(f.partition("=")[::2] for f in args.fields)
        try:
            path = set_fields(args.jobs, args.job, fields)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR {exc}", file=sys.stderr)
            return 1
        print(f"{path}: set {', '.join(fields)}; index rebuilt")
        return 0
    if args.cmd == "lookup":
        path = find_job(args.jobs, args.url)
        if path:
            print(path.as_posix())
        return 0 if path else 1
    profile =load_profile(args.profile, args.overrides)
    if args.cmd == "filter":
        postings = json.loads(args.postings.read_text(encoding="utf-8"))["postings"]
        keep, dropped = filter_postings(postings, profile, args.jobs)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(keep)} candidates -> {args.out}; dropped {len(dropped)}")
        for d in dropped:
            print(f"  drop {d['key']}: {d['reason']}", file=sys.stderr)
        return 0
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    scores = json.loads(args.scores.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        result = write_jobs(candidates, scores, args.jobs, profile["min_score"], now)
    except ValueError as exc:
        print(f"nothing written: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {len(result['written'])}, below min_score {len(result['below_min'])}, "
          f"skipped {len(result['skipped'])}, unscored {len(result['unscored'])}; index rebuilt")
    for key in result["unscored"]:
        print(f"  unscored: {key}", file=sys.stderr)
    return 1 if result["unscored"] else 0


if __name__ == "__main__":
    sys.exit(main())
