from datetime import date

from companies import company_jobs, find, stale_sections, trend_arrow


def profile(companies, slug, **meta):
    companies.mkdir(exist_ok=True)
    lines = "\n".join(f"{k}: {v}" for k, v in meta.items())
    (companies / f"{slug}.md").write_text(f"---\n{lines}\n---\n# {slug}\n", encoding="utf-8")


def job(jobs, key, **meta):
    jobs.mkdir(exist_ok=True)
    lines = "\n".join(f"{k}: {v}" for k, v in meta.items())
    (jobs / f"{key}.md").write_text(f"---\n{lines}\n---\n", encoding="utf-8")


def test_find_matches_slug_name_and_aliases_ignoring_case_and_punctuation(tmp_path):
    profile(tmp_path, "tsmc", name="TSMC", aliases="[台積電, 台灣積體電路製造, Taiwan Semiconductor Mfg.]")

    assert find(tmp_path, "台積電") == "tsmc"
    assert find(tmp_path, "taiwan semiconductor mfg") == "tsmc"
    assert find(tmp_path, "TSMC") == "tsmc"
    assert find(tmp_path, "UMC") is None
    assert find(tmp_path / "missing", "TSMC") is None


def test_stale_sections_use_per_section_ttl():
    meta = {"checked": {"growth": "2026-07-01", "culture": date(2026, 9, 1), "pay": "2026-05-01"}}

    assert stale_sections(meta, date(2026, 10, 6)) == ["growth"]  # 97 days > 90; pay 158 <= 180
    assert stale_sections({}, date(2026, 10, 6)) == ["growth", "culture", "pay"]


def test_trend_arrow(tmp_path):
    profile(tmp_path, "nvidia", trend="shrinking")
    profile(tmp_path, "acme", trend="sideways")

    assert trend_arrow(tmp_path, "nvidia") == "↓"
    assert trend_arrow(tmp_path, "acme") == "?"
    assert trend_arrow(tmp_path, None) == "" and trend_arrow(tmp_path, "nope") == ""


def test_company_jobs_by_link_or_alias_skipping_ignored(tmp_path):
    companies, jobs = tmp_path / "companies", tmp_path / "jobs"
    profile(companies, "nvidia", name="NVIDIA", aliases="[輝達]")
    job(jobs, "nvidia-1", company="NVIDIA", status="new")
    job(jobs, "x-2", company="輝達", status="applied")
    job(jobs, "y-3", company="Other", company_profile="nvidia", status="new")
    job(jobs, "nvidia-4", company="NVIDIA", status="ignored")
    job(jobs, "amd-5", company="AMD", status="new")
    (jobs / "INDEX.md").write_text("# Job Postings\n", encoding="utf-8")

    assert [p.name for p in company_jobs(companies, jobs, "nvidia")] == ["nvidia-1.md", "x-2.md", "y-3.md"]
