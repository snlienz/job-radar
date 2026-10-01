import httpx
import pytest
import yaml

from add_source import append_entry, confirm, count_job_links, default_name, detect_platform, probe

PROFILE = {"include": ["firmware"], "exclude": [], "locations": []}
WORKDAY_URL = "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
LISTING = "<html><body>" + "".join(f'<a href="/jobs/{i}">Engineer {i}</a>' for i in range(5)) + "</body></html>"


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_workday_host_is_api_with_adapter_without_fetching():
    def handler(request):
        raise AssertionError("no request expected")

    found = probe(WORKDAY_URL, "NVIDIA", client(handler))
    assert found["entry"] == {"name": "NVIDIA", "url": WORKDAY_URL, "method": "api", "adapter": "workday"}


def test_static_listing_is_fetch():
    found = probe("https://example.com/careers", "EXAMPLE",
                  client(lambda r: httpx.Response(200, text=LISTING, headers={"content-type": "text/html"})))
    assert found["entry"]["method"] == "fetch"


def test_blocked_site_is_browser():
    found = probe("https://careers.tsmc.com/x", "TSMC", client(lambda r: httpx.Response(403)))
    assert found["entry"]["method"] == "browser"


def test_js_shell_is_browser():
    found = probe("https://example.com/careers", "EXAMPLE",
                  client(lambda r: httpx.Response(200, text="<html><body><div id=app></div></body></html>")))
    assert found["entry"]["method"] == "browser"


def test_platform_without_adapter_is_detected_and_suggested():
    page = "<html><body><div id=app>powered by jobs2web</div></body></html>"
    found = probe("https://careers.example.com/search", "EXAMPLE", client(lambda r: httpx.Response(200, text=page)))
    assert found["entry"]["method"] == "browser" and found["suggest_adapter"] == "successfactors"
    assert detect_platform("https://boards.greenhouse.io/acme") == ("greenhouse", None)


def test_confirm_reports_failure_and_skips_browser():
    entry = {"name": "X", "url": "https://example.com/careers", "method": "fetch"}
    assert confirm(entry, PROFILE, client(lambda r: httpx.Response(200, text="<html></html>")))["ok"] is False
    assert confirm({**entry, "method": "browser"}, PROFILE, client(lambda r: None))["ok"] is None


def test_append_keeps_comments_and_rejects_duplicates(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text("# keep me\nsources:\n  - name: A\n    url: https://a.example/jobs\n    method: browser\n", encoding="utf-8")
    append_entry(path, {"name": "B", "url": "https://b.example/jobs", "method": "api", "adapter": "workday"})

    assert path.read_text(encoding="utf-8").startswith("# keep me")
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["sources"][1] == {
        "name": "B", "url": "https://b.example/jobs", "method": "api", "adapter": "workday"}
    for dup in ({"name": "a", "url": "https://x.example"}, {"name": "C", "url": "https://a.example/jobs/"}):
        with pytest.raises(ValueError):
            append_entry(path, {**dup, "method": "browser"})


def test_names_and_link_counting():
    assert default_name("https://careers.tsmc.com/zh_TW/x") == "TSMC"
    assert default_name("https://nvidia.wd5.myworkdayjobs.com/x") == "NVIDIA"
    assert count_job_links(LISTING, "https://example.com/careers") == 5
