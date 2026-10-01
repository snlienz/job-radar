import json
from pathlib import Path

import httpx

from fetch_jobs import fetch_all, fetch_104, fetch_static, fetch_workday, html_to_text, queries

FIX = Path(__file__).parent / "fixtures"
PROFILE = {"include": ["firmware"], "exclude": [], "locations": ["Taipei"]}
WORKDAY = {"name": "NVIDIA", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
           "method": "api", "adapter": "workday"}
S104 = {"name": 104, "url": "https://www.104.com.tw/jobs/search/", "method": "api", "adapter": "104"}


def fixture(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def workday_handler(request, seen=None):
    if seen is not None:
        seen.append(request)
    if request.method == "POST":
        assert request.url.path == "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
        return httpx.Response(200, json=fixture("workday_search.json"))
    path = request.url.path.removeprefix("/wday/cxs/nvidia/NVIDIAExternalCareerSite")
    return httpx.Response(200, json=fixture("workday_details.json")[path])


def test_workday_returns_normalized_postings():
    postings = fetch_workday(WORKDAY, PROFILE, client(workday_handler))

    assert len(postings) == 2
    first = postings[0]
    assert set(first) == {"source", "company", "id", "title", "location", "url", "jd_text", "posted_at"}
    assert first["company"] == "NVIDIA" and first["id"].startswith("JR")
    assert first["location"].startswith("Taiwan")
    assert first["url"].startswith("https://nvidia.wd5.myworkdayjobs.com/")
    assert "<p>" not in first["jd_text"] and len(first["jd_text"]) > 200
    assert first["posted_at"] == "2026-03-25"


def test_workday_searches_keyword_and_location_together():
    seen = []
    fetch_workday(WORKDAY, PROFILE, client(lambda r: workday_handler(r, seen)))

    assert json.loads(seen[0].content)["searchText"] == "firmware Taipei"


def fixture_104_handler(request):
    if request.url.path == "/jobs/search/api/jobs":
        assert request.headers["referer"] == "https://www.104.com.tw/jobs/search/"
        return httpx.Response(200, json=fixture("104_search.json"))
    if request.url.path == "/job/ajax/content/7abc1":
        return httpx.Response(200, json=fixture("104_detail.json"))
    return httpx.Response(404)


def test_104_returns_normalized_postings_with_full_jd_when_detail_works():
    postings = fetch_104(S104, PROFILE, client(fixture_104_handler))

    by_id = {p["id"]: p for p in postings}
    assert by_id["7abc1"] == {
        "source": "104",
        "company": "範例科技股份有限公司",
        "id": "7abc1",
        "title": "韌體工程師 Firmware Engineer",
        "location": "新竹市",
        "url": "https://www.104.com.tw/job/7abc1?jobsource=search",
        "jd_text": by_id["7abc1"]["jd_text"],
        "posted_at": "2026-10-01",
    }
    assert "撰寫 C/C++ driver" in by_id["7abc1"]["jd_text"] and "3年以上" in by_id["7abc1"]["jd_text"]
    assert by_id["7abc2"]["jd_text"] == "Embedded C/C++ (snippet)"  # detail 404 falls back to the snippet


def test_104_maps_known_city_to_area_code():
    seen = []

    def handler(request):
        seen.append(request)
        return fixture_104_handler(request)

    fetch_104(S104, PROFILE, client(handler))

    assert seen[0].url.params["area"] == "6001001000" and seen[0].url.params["keyword"] == "firmware"


def test_bot_challenge_is_reported_as_blocked_and_other_sources_still_run():
    def handler(request):
        if request.url.host == "www.104.com.tw":
            return httpx.Response(403, headers={"cf-mitigated": "challenge"}, text="Just a moment...")
        return workday_handler(request)

    sources = [S104, WORKDAY, {"name": "TSMC", "url": "https://careers.tsmc.com", "method": "browser"}]
    result = fetch_all(sources, PROFILE, client(handler))

    assert len(result["postings"]) == 2
    assert [(e["source"], e["blocked"]) for e in result["errors"]] == [("104", True)]
    assert result["browser"] == ["TSMC"]


def test_unexpected_failure_is_reported_not_raised():
    result = fetch_all([WORKDAY], PROFILE, client(lambda r: httpx.Response(500)))

    assert result["postings"] == [] and result["errors"][0]["blocked"] is False


def test_static_page_collects_job_links_and_their_text():
    pages = {
        "/careers": '<a href="/jobs/1">Firmware Engineer</a><a href="/about">About</a><a href="/jobs/2">QA</a>',
        "/jobs/1": "<nav>menu</nav><h1>Firmware Engineer</h1><p>Write drivers.</p><script>x()</script>",
        "/jobs/2": "<p>Test things.</p>",
    }
    source = {"name": "Acme", "url": "https://acme.test/careers", "method": "fetch"}

    postings = fetch_static(source, PROFILE, client(lambda r: httpx.Response(200, text=pages[r.url.path])))

    assert [p["url"] for p in postings] == ["https://acme.test/jobs/1", "https://acme.test/jobs/2"]
    assert postings[0]["title"] == "Firmware Engineer" and postings[0]["id"] == "jobs-1"
    assert "Write drivers." in postings[0]["jd_text"] and "menu" not in postings[0]["jd_text"]
    assert "x()" not in postings[0]["jd_text"]


def test_html_to_text_keeps_list_and_paragraph_breaks():
    assert html_to_text("<p>Intro</p><ul><li>One</li><li>Two</li></ul>") == "Intro\n- One\n- Two"


def test_queries_cross_keywords_with_locations():
    profile = {"include": ["firmware", "embedded"], "locations": ["Taipei", "Hsinchu"]}
    assert queries(profile) == ["firmware Taipei", "firmware Hsinchu", "embedded Taipei", "embedded Hsinchu"]
    assert queries({"include": [], "locations": []}) == [""]
