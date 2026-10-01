"""Fetch Job Postings from `api` / `fetch` Job Sources as normalized JSON.

Each posting: {source, company, id, title, location, url, jd_text, posted_at}. `browser` sources are
not fetched here (the agent drives them through Claude in Chrome) and are listed under `browser`.
A source that cannot be fetched (blocked, network, changed format) is reported under `errors`
instead of aborting the run.
"""
import argparse
import itertools
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from lxml import html as lxml_html

from search_profile import load_profile

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
DEFAULT_LIMIT = 40  # postings per query per source


class Blocked(Exception):
    """The site refused a scripted client (bot challenge, 403). Fall back to the browser method."""


def html_to_text(fragment: str) -> str:
    if not fragment.strip():
        return ""
    root = lxml_html.fromstring(f"<div>{fragment}</div>")
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag == "br":
            el.tail = "\n" + (el.tail or "")
        elif el.tag == "li":
            el.text = "- " + (el.text or "")
            el.tail = "\n" + (el.tail or "")
        elif el.tag in ("p", "div", "h1", "h2", "h3", "h4", "ul", "ol", "tr"):
            el.tail = "\n" + (el.tail or "")
    text = root.text_content().replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line.strip() for line in text.splitlines())).strip()


def queries(profile: dict) -> list[str]:
    """One search string per keyword x location; empty profile fields mean "no restriction"."""
    return [
        " ".join(p for p in pair if p)
        for pair in itertools.product(profile["include"] or [""], profile["locations"] or [""])
    ]


def _check(response: httpx.Response) -> httpx.Response:
    if response.status_code in (403, 429) or response.headers.get("cf-mitigated"):
        raise Blocked(f"{response.url.host} refused the request (HTTP {response.status_code})")
    response.raise_for_status()
    return response


# --- Workday -----------------------------------------------------------------------------------

def _workday_base(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    tenant = parsed.netloc.split(".")[0]
    parts = [p for p in parsed.path.split("/") if p and not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", p)]
    return parsed.netloc, f"/wday/cxs/{tenant}/{parts[0]}"


def fetch_workday(source: dict, profile: dict, client: httpx.Client, limit: int = DEFAULT_LIMIT) -> list[dict]:
    host, api = _workday_base(source["url"])
    paths: dict[str, dict] = {}
    for text in queries(profile):
        offset = 0
        while offset < limit:
            data = _check(client.post(
                f"https://{host}{api}/jobs",
                json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": text},
            )).json()
            for posting in data["jobPostings"]:
                paths.setdefault(posting["externalPath"], posting)
            offset += 20
            if offset >= data["total"]:
                break
    postings = []
    for path in paths:
        info = _check(client.get(f"https://{host}{api}{path}")).json()["jobPostingInfo"]
        locations = [info["location"], *info.get("additionalLocations", [])]
        postings.append({
            "source": str(source["name"]),
            "company": str(source["name"]),
            "id": info["jobReqId"],
            "title": info["title"],
            "location": "; ".join(dict.fromkeys(locations)),
            "url": info["externalUrl"],
            "jd_text": html_to_text(info["jobDescription"]),
            "posted_at": info.get("startDate"),
        })
    return postings


# --- 104 ---------------------------------------------------------------------------------------

AREAS = {  # 104 area codes for the cities profiles usually name
    "taipei": "6001001000", "台北": "6001001000", "new taipei": "6001002000", "新北": "6001002000",
    "taoyuan": "6001005000", "桃園": "6001005000", "hsinchu": "6001006000", "新竹": "6001006000",
    "taichung": "6001008000", "台中": "6001008000", "tainan": "6001014000", "台南": "6001014000",
    "kaohsiung": "6001016000", "高雄": "6001016000",
}
SEARCH_104 = "https://www.104.com.tw/jobs/search/api/jobs"
DETAIL_104 = "https://www.104.com.tw/job/ajax/content/{}"


def _date_104(value: str | None) -> str | None:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if value and re.fullmatch(r"\d{8}", value) else None


def _flat(value) -> str:
    if isinstance(value, list):
        return ", ".join(_flat(v) for v in value)
    if isinstance(value, dict):
        return str(value.get("description") or value.get("name") or "")
    return str(value)


def fetch_104(source: dict, profile: dict, client: httpx.Client, limit: int = DEFAULT_LIMIT) -> list[dict]:
    found: dict[str, dict] = {}
    pairs = itertools.product(profile["include"] or [""], profile["locations"] or [""])
    for keyword, location in pairs:
        page = 1
        while True:
            params = {"keyword": keyword, "page": page, "order": 15}  # 15 = newest first
            if location.casefold() in AREAS:
                params["area"] = AREAS[location.casefold()]
            elif location:
                params["keyword"] = f"{keyword} {location}".strip()
            data = _check(client.get(SEARCH_104, params=params, headers={"Referer": source["url"]})).json()
            for item in data["data"]:
                found.setdefault(item["jobNo"], item)
            last = data.get("metadata", {}).get("pagination", {}).get("lastPage", 1)
            if page >= last or page * 20 >= limit:
                break
            page += 1
    postings = []
    for job_no, item in found.items():
        jd = item.get("descWithoutHighlight", "")
        try:  # the list only has a snippet; the detail endpoint has the full JD
            detail = _check(client.get(
                DETAIL_104.format(job_no), headers={"Referer": f"https://www.104.com.tw/job/{job_no}"}
            )).json()["data"]
            jd = detail["jobDetail"]["jobDescription"]
            condition = detail.get("condition", {})
            extra = [f"{label}: {_flat(condition[key])}" for key, label in
                     (("workExp", "Experience"), ("edu", "Education"), ("specialty", "Skills")) if condition.get(key)]
            jd = "\n".join([jd, *extra]) if extra else jd
        except (httpx.HTTPError, KeyError, ValueError):
            pass
        postings.append({
            "source": str(source["name"]),
            "company": item["custName"],
            "id": job_no,
            "title": item["jobName"],
            "location": item.get("jobAddrNoDesc", ""),
            "url": urljoin("https://www.104.com.tw/", item["link"]["job"]),
            "jd_text": jd,
            "posted_at": _date_104(item.get("appearDate")),
        })
    return postings


# --- generic static pages ----------------------------------------------------------------------

def fetch_static(source: dict, profile: dict, client: httpx.Client, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Listing page of job links (`link_pattern` regex on the href, default job-ish words)."""
    pattern = re.compile(source.get("link_pattern", r"job|career|position|opening|requisition"), re.I)
    listing = lxml_html.fromstring(_check(client.get(source["url"])).text)
    listing.make_links_absolute(source["url"])
    links: dict[str, str] = {}
    for a in listing.iter("a"):
        href = (a.get("href") or "").split("#")[0]
        title = " ".join(a.text_content().split())
        if href and title and pattern.search(href) and href.rstrip("/") != source["url"].rstrip("/"):
            links.setdefault(href, title)
    postings = []
    for url, title in list(links.items())[:limit]:
        page = lxml_html.fromstring(_check(client.get(url)).text)
        for el in page.xpath("//script|//style|//nav|//header|//footer"):
            el.drop_tree()
        postings.append({
            "source": str(source["name"]),
            "company": str(source["name"]),
            "id": re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.casefold()).strip("-") or "job",
            "title": title,
            "location": "",
            "url": url,
            "jd_text": html_to_text(lxml_html.tostring(page, encoding="unicode")),
            "posted_at": None,
        })
    return postings


ADAPTERS = {"workday": fetch_workday, "104": fetch_104}


def fetch_all(sources: list[dict], profile: dict, client: httpx.Client, limit: int = DEFAULT_LIMIT) -> dict:
    result = {"postings": [], "browser": [], "errors": []}
    for source in sources:
        method = source.get("method")
        if method == "browser":
            result["browser"].append(str(source["name"]))
            continue
        adapter = ADAPTERS.get(source.get("adapter")) if method == "api" else fetch_static
        try:
            if adapter is None:
                raise ValueError(f"no adapter {source.get('adapter')!r} for method {method!r}")
            result["postings"] += adapter(source, profile, client, limit)
        except Blocked as exc:
            result["errors"].append({"source": str(source["name"]), "blocked": True, "error": str(exc)})
        except Exception as exc:  # one broken source must not hide the others
            result["errors"].append({"source": str(source["name"]), "blocked": False, "error": f"{type(exc).__name__}: {exc}"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("overrides", nargs="*", help="keywords=a,b location=Taipei ... (see profile.py)")
    parser.add_argument("--sources", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--profile", type=Path, default=Path("config/profile.yaml"))
    parser.add_argument("--only", help="fetch just this source name")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="postings per query per source")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    profile = load_profile(args.profile, args.overrides)
    sources = yaml.safe_load(args.sources.read_text(encoding="utf-8"))["sources"]
    if args.only:
        sources = [s for s in sources if str(s["name"]) == args.only]
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        result = fetch_all(sources, profile, client, args.limit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(result['postings'])} postings -> {args.out}")
    for err in result["errors"]:
        print(f"{'BLOCKED' if err['blocked'] else 'ERROR'} {err['source']}: {err['error']}", file=sys.stderr)
    if result["browser"]:
        print("browser sources (drive with Claude in Chrome): " + ", ".join(map(str, result["browser"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
