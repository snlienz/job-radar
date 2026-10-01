from pathlib import Path

import yaml

from validate import validate_tailored

SCHEMA = Path(__file__).parent.parent / "schemas" / "tailored.schema.json"


def master_data():
    return {
        "basics": {"name": "Steven Lien", "email": "me@example.com"},
        "experience": [
            {
                "id": "barco",
                "company": "Barco",
                "title": "Software Engineer",
                "period": {"start": "2019-03", "end": "present"},
                "achievements": [
                    {"id": "wgc-capture", "text": "Integrated WGC.", "sources": []},
                    {"id": "sift-swap", "text": "Replaced SIFT.", "sources": []},
                    {"id": "secret", "text": "Private work.", "tags": ["do-not-use"], "sources": []},
                ],
            },
            {
                "id": "ftdi",
                "company": "FTDI",
                "title": "Engineer",
                "period": {"start": "2014", "end": "2018-06"},
                "achievements": [{"id": "smart-home", "text": "Built a stack.", "sources": []}],
            },
        ],
        "skills": [{"name": "C++"}, {"name": "Python"}],
        "education": [{"school": "NTU", "degree": "BS"}],
    }


def tailored(**overrides):
    data = {
        "job": "nvidia-1",
        "basics": {"name": "Steven Lien", "email": "me@example.com", "headline": "Capture engineer"},
        "experience": [
            {
                "id": "barco",
                "company": "Barco",
                "title": "Software Engineer",
                "period": {"start": "2019-03", "end": "present"},
                "achievements": [{"source_id": "wgc-capture", "text": "Shipped WGC capture."}],
            }
        ],
        "skills": [{"name": "c++"}],
        "education": [{"school": "NTU", "degree": "BS"}],
    }
    data.update(overrides)
    return data


def check(tmp_path, data, master=None):
    master_path = tmp_path / "master.yaml"
    master_path.write_text(yaml.safe_dump(master or master_data(), allow_unicode=True), encoding="utf-8")
    path = tmp_path / "tailored.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return validate_tailored(path, SCHEMA, master_path)


def test_valid_tailored_resume_has_no_errors(tmp_path):
    assert check(tmp_path, tailored()) == []


def test_bullet_without_source_id_is_rejected(tmp_path):
    data = tailored()
    del data["experience"][0]["achievements"][0]["source_id"]

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "source_id" in errors[0]


def test_bullet_with_unknown_source_id_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["achievements"][0]["source_id"] = "made-up"

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "made-up" in errors[0]


def test_bullet_from_another_experience_entry_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["achievements"][0]["source_id"] = "smart-home"

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "smart-home" in errors[0] and "barco" in errors[0]


def test_do_not_use_achievement_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["achievements"][0]["source_id"] = "secret"

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "secret" in errors[0] and "do-not-use" in errors[0]


def test_same_achievement_used_twice_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["achievements"].append({"source_id": "wgc-capture", "text": "Again."})

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "wgc-capture" in errors[0] and "twice" in errors[0]


def test_project_bullets_are_checked_against_the_project(tmp_path):
    master = master_data()
    master["projects"] = [
        {"id": "radar", "name": "Radar", "achievements": [{"id": "radar-fw", "text": "x", "sources": []}]}
    ]
    ok = tailored(projects=[{"id": "radar", "name": "Radar",
                             "achievements": [{"source_id": "radar-fw", "text": "Built FW."}]}])
    bad = tailored(projects=[{"id": "radar", "name": "Radar",
                              "achievements": [{"source_id": "wgc-capture", "text": "Stolen."}]}])

    assert check(tmp_path, ok, master) == []
    assert "wgc-capture" in check(tmp_path, bad, master)[0]


def test_unknown_experience_id_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["id"] = "acme"

    errors = check(tmp_path, data)

    assert len(errors) == 1
    assert "acme" in errors[0]


def test_changed_company_title_or_period_is_rejected(tmp_path):
    data = tailored()
    data["experience"][0]["title"] = "Principal Engineer"
    data["experience"][0]["period"] = {"start": "2015"}

    errors = check(tmp_path, data)

    assert len(errors) == 2
    assert any("title" in e for e in errors) and any("period" in e for e in errors)


def test_skill_not_in_master_is_rejected_case_insensitively(tmp_path):
    ok = tailored(skills=[{"name": "PYTHON"}])
    bad = tailored(skills=[{"name": "Rust"}])

    assert check(tmp_path, ok) == []
    errors = check(tmp_path, bad)
    assert len(errors) == 1 and "Rust" in errors[0]


def test_education_not_in_master_is_rejected(tmp_path):
    data = tailored(education=[{"school": "MIT", "degree": "PhD"}])

    errors = check(tmp_path, data)

    assert len(errors) == 1 and "MIT" in errors[0]


def test_changed_basics_fact_is_rejected_but_headline_and_summary_may_differ(tmp_path):
    ok = tailored()
    ok["basics"]["summary"] = "Tailored pitch."
    bad = tailored()
    bad["basics"]["email"] = "other@example.com"

    assert check(tmp_path, ok) == []
    errors = check(tmp_path, bad)
    assert len(errors) == 1 and "email" in errors[0]
