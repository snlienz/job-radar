from pathlib import Path

import yaml

from validate import validate_file

SCHEMA = Path(__file__).parent.parent / "schemas" / "master.schema.json"


def master(**overrides):
    data = {
        "basics": {"name": "Steven Lien"},
        "experience": [
            {
                "id": "barco",
                "company": "Barco",
                "title": "Software Engineer",
                "period": {"start": "2019-03", "end": "present"},
                "achievements": [
                    {
                        "id": "wgc-capture",
                        "text": "Integrated Windows.Graphics.Capture, cutting crash rate by 30%.",
                        "sources": [{"file": "wiki/wgc.md", "quote": "整合 WGC，crash rate 降低 30%"}],
                    }
                ],
            }
        ],
    }
    data.update(overrides)
    return data


def write_master(tmp_path, data):
    raw = tmp_path / "raw"
    (raw / "wiki").mkdir(parents=True, exist_ok=True)
    (raw / "wiki" / "wgc.md").write_text("整合 WGC，crash rate 降低 30%", encoding="utf-8")
    path = tmp_path / "master.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path, raw


def test_valid_master_has_no_errors(tmp_path):
    path, raw = write_master(tmp_path, master())

    assert validate_file(path, SCHEMA, raw, tmp_path / "extracted") == []


def test_schema_violation_is_reported_with_its_location(tmp_path):
    data = master()
    del data["experience"][0]["company"]
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw, tmp_path / "extracted")

    assert len(errors) == 1
    assert errors[0].startswith("experience/0:") and "company" in errors[0]


def test_source_file_missing_from_raw_dir_is_reported(tmp_path):
    data = master()
    data["experience"][0]["achievements"][0]["sources"][0]["file"] = "wiki/gone.md"
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw, tmp_path / "extracted")

    assert len(errors) == 1
    assert "wgc-capture" in errors[0] and "wiki/gone.md" in errors[0]


def test_duplicate_achievement_ids_are_reported(tmp_path):
    data = master()
    first = data["experience"][0]["achievements"][0]
    data["projects"] = [{"id": "p1", "name": "P1", "achievements": [dict(first)]}]
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw, tmp_path / "extracted")

    assert len(errors) == 1
    assert "duplicate" in errors[0] and "wgc-capture" in errors[0]


def test_quote_not_in_source_is_reported_with_achievement_id(tmp_path):
    data = master()
    data["experience"][0]["achievements"][0]["sources"][0]["quote"] = "整合 WGC，crash 降低"
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw, tmp_path / "extracted")

    assert len(errors) == 1
    assert "wgc-capture" in errors[0] and "wiki/wgc.md" in errors[0] and "整合 WGC，crash" in errors[0]


def test_quote_matches_across_different_whitespace(tmp_path):
    data = master()
    data["experience"][0]["achievements"][0]["sources"][0]["quote"] = "整合\n  WGC"
    path, raw = write_master(tmp_path, data)

    assert validate_file(path, SCHEMA, raw, tmp_path / "extracted") == []


def test_quote_is_checked_against_extracted_text_for_binary_formats(tmp_path):
    data = master()
    data["experience"][0]["achievements"][0]["sources"][0] = {
        "file": "reviews/2024.docx",
        "quote": "crash rate -30%",
    }
    path, raw = write_master(tmp_path, data)
    (raw / "reviews").mkdir()
    (raw / "reviews" / "2024.docx").write_bytes(b"PK")
    extracted = tmp_path / "extracted"

    assert "no extracted text" in validate_file(path, SCHEMA, raw, extracted)[0]

    (extracted / "reviews").mkdir(parents=True)
    (extracted / "reviews" / "2024.docx.txt").write_text("KPI	crash rate -30%", encoding="utf-8")
    assert validate_file(path, SCHEMA, raw, extracted) == []


def test_dangling_skill_evidence_id_is_reported(tmp_path):
    data = master(skills=[{"name": "C++", "evidence": ["wgc-capture", "nope"]}])
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw, tmp_path / "extracted")

    assert len(errors) == 1
    assert "C++" in errors[0] and "nope" in errors[0]
