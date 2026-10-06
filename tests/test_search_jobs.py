from pathlib import Path

import pytest
import yaml

from search_jobs import (filter_postings, known_jobs, posting_key, read_job, rebuild_index, set_status,
                         write_jobs)
from search_profile import load_profile


def posting(**overrides):
    base = {"source": "NVIDIA", "company": "NVIDIA", "id": "JR1", "title": "Firmware Engineer",
            "location": "Taiwan, Taipei", "url": "https://x.test/jr1", "jd_text": "Write C drivers.",
            "posted_at": "2026-09-30"}
    return {**base, **overrides}


PROFILE = {"include": ["firmware"], "exclude": ["intern"], "locations": ["Taipei", "Hsinchu"],
           "industries": [], "seniority": "senior", "min_score": 60}


def test_profile_overrides_replace_fields(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump({"keywords": {"include": ["a"], "exclude": ["b"]},
                                    "locations": ["Taipei"], "min_score": 60}), encoding="utf-8")

    profile = load_profile(path, ["keywords=firmware,embedded", "min_score=70", "location=Hsinchu"])

    assert profile["include"] == ["firmware", "embedded"] and profile["exclude"] == ["b"]
    assert profile["locations"] == ["Hsinchu"] and profile["min_score"] == 70
    with pytest.raises(ValueError):
        load_profile(path, ["nonsense=1"])


def test_hard_filter_keywords_and_locations(tmp_path):
    postings = [
        posting(id="keep"),
        posting(id="nokw", title="Sales", jd_text="Sell things"),
        posting(id="excluded", title="Firmware Intern"),
        posting(id="elsewhere", location="US, CA, Santa Clara"),
        posting(id="zh", location="新竹市", title="韌體 firmware"),
        posting(id="nowhere", location=""),
    ]
    postings = [{**p, "url": f"https://x.test/{p['id']}"} for p in postings]

    keep, dropped = filter_postings(postings, PROFILE, tmp_path)

    assert [p["id"] for p in keep] == ["keep", "zh", "nowhere"]
    reasons = {d["key"]: d["reason"] for d in dropped}
    assert "include keyword" in reasons["nvidia-nokw"]
    assert "intern" in reasons["nvidia-excluded"]
    assert "location" in reasons["nvidia-elsewhere"]


def test_exclude_keywords_match_the_title_only(tmp_path):
    jd = "Firmware role. Intern or full time; experience via an internship counts."

    keep, _ = filter_postings([posting(jd_text=jd)], PROFILE, tmp_path)

    assert len(keep) == 1


def test_empty_profile_keeps_everything(tmp_path):
    empty = {"include": [], "exclude": [], "locations": []}

    keep, _ = filter_postings([posting()], empty, tmp_path)

    assert len(keep) == 1


def score(n, **extra):
    return {"score": n, "summary": "Good fit.", "strengths": ["C drivers"], "gaps": ["No GPU"], **extra}


def run_write(jobs, candidates, scores, min_score=60):
    return write_jobs(candidates, scores, jobs, min_score, "2026-10-01T00:00:00Z")


def test_write_creates_job_files_and_sorted_index(tmp_path):
    jobs = tmp_path / "jobs"
    cands = [{**posting(id="a", url="https://x.test/a"), "key": "nvidia-a"},
             {**posting(id="b", url="https://x.test/b", title="Other | Role"), "key": "nvidia-b"},
             {**posting(id="c", url="https://x.test/c"), "key": "nvidia-c"}]

    result = run_write(jobs, cands, {"nvidia-a": score(70), "nvidia-b": score(90), "nvidia-c": score(40)})

    assert result["written"] == ["nvidia-a", "nvidia-b"] and result["below_min"] == ["nvidia-c"]
    meta, body = read_job(jobs / "nvidia-a.md")
    assert meta["url"] == "https://x.test/a" and meta["status"] == "new" and meta["score"] == 70
    assert meta["fetched_at"] == "2026-10-01T00:00:00Z"
    assert "No GPU" in body and "Write C drivers." in body
    lines = (jobs / "INDEX.md").read_text(encoding="utf-8").splitlines()
    assert "[Other / Role](nvidia-b.md)" in lines[4] and "(nvidia-a.md)" in lines[5]  # 90 before 70
    assert not (jobs / "nvidia-c.md").exists()


def test_write_includes_interview_odds_risks_and_prep(tmp_path):
    jobs = tmp_path / "jobs"
    cands = [{**posting(id="a", url="https://x.test/a"), "key": "nvidia-a"},
             {**posting(id="b", url="https://x.test/b"), "key": "nvidia-b"}]
    scores = {"nvidia-a": score(70, interview_odds="55-65%", risks=["Salary below current level"],
                                prep=["Try the vendor toolchain"]),
              "nvidia-b": score(65)}

    run_write(jobs, cands, scores)

    meta, body = read_job(jobs / "nvidia-a.md")
    assert meta["interview_odds"] == "55-65%"
    assert "**Interview odds:** 55-65%" in body
    assert "**Risks**\n- Salary below current level" in body and "**Prep**\n- Try the vendor toolchain" in body
    meta_b, body_b = read_job(jobs / "nvidia-b.md")
    assert "interview_odds" not in meta_b and "**Risks**" not in body_b and "Interview odds" not in body_b
    lines = (jobs / "INDEX.md").read_text(encoding="utf-8").splitlines()
    assert lines[2].startswith("| Score | Odds |")
    assert lines[4].startswith("| 70 | 55-65% |") and lines[5].startswith("| 65 |  |")


def test_rerun_does_not_duplicate_or_overwrite(tmp_path):
    jobs = tmp_path / "jobs"
    cand = {**posting(), "key": "nvidia-jr1"}
    run_write(jobs, [cand], {"nvidia-jr1": score(80)})
    path = jobs / "nvidia-jr1.md"
    meta, body = read_job(path)
    path.write_text(path.read_text(encoding="utf-8").replace("status: new", "status: shortlisted"), encoding="utf-8")

    keep, dropped = filter_postings([posting()], PROFILE, jobs)
    assert keep == [] and "already in jobs" in dropped[0]["reason"]

    result = run_write(jobs, [cand], {"nvidia-jr1": score(95)})
    assert result["skipped"] == ["nvidia-jr1"]
    assert read_job(path)[0]["status"] == "shortlisted" and read_job(path)[0]["score"] == 80
    assert len(list(jobs.glob("nvidia-*.md"))) == 1


def test_ignored_jobs_are_skipped_by_filter_and_hidden_from_index(tmp_path):
    jobs = tmp_path / "jobs"
    cand = {**posting(), "key": "nvidia-jr1"}
    run_write(jobs, [cand], {"nvidia-jr1": score(80)})
    path = jobs / "nvidia-jr1.md"
    path.write_text(path.read_text(encoding="utf-8").replace("status: new", "status: ignored"), encoding="utf-8")

    keep, dropped = filter_postings([posting(url="https://x.test/jr1/")], PROFILE, jobs)  # trailing slash
    rebuild_index(jobs)

    assert keep == [] and dropped[0]["reason"] == "ignored"
    assert "nvidia-jr1" not in (jobs / "INDEX.md").read_text(encoding="utf-8")


def test_duplicate_urls_within_one_run_are_dropped(tmp_path):
    keep, dropped = filter_postings([posting(), posting()], PROFILE, tmp_path)

    assert len(keep) == 1 and dropped[0]["reason"] == "duplicate in this run"


def test_unscored_and_invalid_scores(tmp_path):
    cand = {**posting(), "key": "nvidia-jr1"}

    assert run_write(tmp_path / "j", [cand], {})["unscored"] == ["nvidia-jr1"]
    with pytest.raises(ValueError):
        run_write(tmp_path / "j", [cand], {"nvidia-jr1": score(150)})


def test_posting_key_is_company_and_id_slug():
    assert posting_key(posting(company="Example Corp.", id="7ABC1")) == "example-corp-7abc1"
    assert posting_key(posting(company="範例科技", id="7abc1")) == "範例科技-7abc1"


def test_one_bad_score_writes_nothing(tmp_path):
    jobs = tmp_path / "jobs"
    cands = [{**posting(id="a", url="https://x.test/a"), "key": "nvidia-a"},
             {**posting(id="b", url="https://x.test/b"), "key": "nvidia-b"}]

    with pytest.raises(ValueError):
        run_write(jobs, cands, {"nvidia-a": score(80), "nvidia-b": score(101)})

    assert not jobs.exists() or not list(jobs.glob("*.md"))


def test_set_status_changes_only_the_status_and_rebuilds_index(tmp_path):
    jobs = tmp_path / "jobs"
    run_write(jobs, [{**posting(), "key": "nvidia-jr1"}], {"nvidia-jr1": score(80)})
    path = jobs / "nvidia-jr1.md"
    before = path.read_text(encoding="utf-8")

    set_status(jobs, "nvidia-jr1", "applied")

    assert path.read_text(encoding="utf-8") == before.replace("status: new", "status: applied")
    assert "| applied |" in (jobs / "INDEX.md").read_text(encoding="utf-8")
    set_status(jobs, "jobs/nvidia-jr1.md", "ignored")  # a job file path works too
    assert read_job(path)[0]["status"] == "ignored"
    assert "nvidia-jr1" not in (jobs / "INDEX.md").read_text(encoding="utf-8")


def test_set_status_rejects_unknown_status_and_missing_job(tmp_path):
    jobs = tmp_path / "jobs"
    run_write(jobs, [{**posting(), "key": "nvidia-jr1"}], {"nvidia-jr1": score(80)})

    with pytest.raises(ValueError, match="unknown status"):
        set_status(jobs, "nvidia-jr1", "hired")
    with pytest.raises(FileNotFoundError):
        set_status(jobs, "nvidia-nope", "applied")
    assert read_job(jobs / "nvidia-jr1.md")[0]["status"] == "new"
