"""Probe a careers-site URL, pick the cheapest fetch method that works and add it to config/sources.yaml.

Order of preference (ADR 0003): `api` (a platform with an adapter in fetch_jobs.py) > `fetch` (static
HTML with job links) > `browser`. A site that refuses scripted access, or whose HTML has no job links,
is `browser`; the script cannot confirm those, so the agent checks them in Chrome.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml
from lxml import html as lxml_html

from fetch_jobs import HEADERS, Blocked, _check, fetch_all
from search_profile import load_profile

MIN_JOB_LINKS = 3
JOB_LINK = re.compile(r"job|career|position|opening|requisition", re.I)
GENERIC_LABELS = {"www", "careers", "career", "jobs", "com", "tw", "org", "net", "co"}

# host suffix -> (platform, adapter in fetch_jobs.ADAPTERS or None)
PLATFORMS = {
    "myworkdayjobs.com": ("workday", "workday"),
    "104.com.tw": ("104", "104"),
    "greenhouse.io": ("greenhouse", None),
    "lever.co": ("lever", None),
    "successfactors.com": ("successfactors", None),
    "successfactors.eu": ("successfactors", None),
    "ashbyhq.com": ("ashby", None),
    "smartrecruiters.com": ("smartrecruiters", None),
    "icims.com": ("icims", None),
}
PAGE_MARKERS = {  # platforms on a company's own domain, recognised from the HTML
    "successfactors": ("successfactors", "jobs2web", "career_ns=job_listing"),
    "greenhouse": ("boards.greenhouse.io", "grnhse"),
    "lever": ("jobs.lever.co",),
}


def detect_platform(url: str, page_html: str = "") -> tuple[str | None, str | None]:
    """(platform, adapter name or None) from the host, else from markers in the page HTML."""
    host = urlparse(url).netloc.casefold()
    for suffix, found in PLATFORMS.items():
        if host == suffix or host.endswith("." + suffix):
            return found
    lowered = page_html.casefold()
    for platform, markers in PAGE_MARKERS.items():
        if any(m in lowered for m in markers):
            return platform, None
    return None, None


def default_name(url: str) -> str:
    host = urlparse(url).netloc.split(":")[0]
    labels = [l for l in host.casefold().split(".") if l not in GENERIC_LABELS]
    return labels[0].upper() if labels else host


def count_job_links(page_html: str, url: str) -> int:
    page = lxml_html.fromstring(page_html)
    page.make_links_absolute(url)
    links = {
        a.get("href").split("#")[0] for a in page.iter("a")
        if a.get("href") and a.text_content().strip() and JOB_LINK.search(a.get("href"))
    }
    links.discard(url)
    links.discard(url.rstrip("/"))
    return len(links)


def probe(url: str, name: str, client: httpx.Client) -> dict:
    """Return {entry, reason, platform, suggest_adapter}; `entry` is the sources.yaml item."""
    platform, adapter = detect_platform(url)
    if adapter:
        return {"entry": {"name": name, "url": url, "method": "api", "adapter": adapter}, "platform": platform,
                "suggest_adapter": None, "reason": f"{platform} platform with a built-in adapter"}

    def browser(reason: str, suggest: str | None) -> dict:
        return {"entry": {"name": name, "url": url, "method": "browser"}, "platform": platform,
                "suggest_adapter": suggest, "reason": reason}

    try:
        response = _check(client.get(url))
    except Blocked as exc:
        return browser(f"scripted access refused ({exc}); needs the browser", platform)
    except httpx.HTTPError as exc:
        raise SystemExit(f"cannot reach {url}: {type(exc).__name__}: {exc}")

    platform = platform or detect_platform(url, response.text)[0]
    if "json" in response.headers.get("content-type", ""):
        return browser("JSON endpoint, but no adapter understands it; needs the browser until one is added",
                       platform or "this JSON endpoint")
    links = count_job_links(response.text, str(response.url))
    if links >= MIN_JOB_LINKS:
        return {"entry": {"name": name, "url": url, "method": "fetch"}, "platform": platform,
                "suggest_adapter": platform, "reason": f"static HTML with {links} job links"}
    return browser(f"only {links} job links in the static HTML (rendered by JavaScript); needs the browser", platform)


def confirm(entry: dict, profile: dict, client: httpx.Client) -> dict:
    """One real fetch with the new entry. browser sources cannot be confirmed from here."""
    if entry["method"] == "browser":
        return {"ok": None, "detail": "browser source: open it in Chrome to confirm"}
    result = fetch_all([entry], profile, client, limit=1)
    if result["errors"]:
        return {"ok": False, "detail": result["errors"][0]["error"]}
    if not result["postings"]:
        return {"ok": False, "detail": "fetched but found no postings (the profile keywords may not match)"}
    first = result["postings"][0]
    return {"ok": True, "detail": f"{len(result['postings'])} posting(s), e.g. {first['title']!r}"}


def append_entry(path: Path, entry: dict) -> None:
    """Append without rewriting the file, so its comments survive. Raises on a duplicate name or URL."""
    text = path.read_text(encoding="utf-8")
    for existing in yaml.safe_load(text)["sources"]:
        if (str(existing["name"]).casefold() == str(entry["name"]).casefold()
                or existing["url"].rstrip("/") == entry["url"].rstrip("/")):
            raise ValueError(f"source already present: {existing['name']} ({existing['url']})")
    lines = [f"  - name: {json.dumps(entry['name'], ensure_ascii=False)}",
             f"    url: {entry['url']}",
             f"    method: {entry['method']}"]
    if entry.get("adapter"):
        lines.append(f"    adapter: {json.dumps(entry['adapter'])}")
    path.write_text(text.rstrip("\n") + "\n\n" + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--name", help="source name (default: derived from the host)")
    parser.add_argument("--sources", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--profile", type=Path, default=Path("config/profile.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="probe and confirm but do not write")
    args = parser.parse_args()
    if not re.match(r"https?://", args.url):
        parser.error("url must start with http:// or https://")

    profile = load_profile(args.profile)
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        found = probe(args.url, args.name or default_name(args.url), client)
        test = confirm(found["entry"], profile, client)
        if test["ok"] is False:  # the cheap method did not actually work
            found["entry"] = {"name": found["entry"]["name"], "url": args.url, "method": "browser"}
            found["reason"] += f"; test fetch failed ({test['detail']}), fell back to browser"
            test = confirm(found["entry"], profile, client)

    entry = found["entry"]
    print(f"{entry['name']}: method={entry['method']}" + (f" adapter={entry['adapter']}" if entry.get("adapter") else ""))
    print(f"reason: {found['reason']}")
    print(f"test fetch: {test['detail']}")
    if found["suggest_adapter"] and not entry.get("adapter"):
        print(f"suggest: {found['suggest_adapter']} has no adapter in scripts/fetch_jobs.py; add one if it recurs")
    if args.dry_run:
        return 0
    try:
        append_entry(args.sources, entry)
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    print(f"added to {args.sources}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
