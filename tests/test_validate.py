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
    (raw / "wiki" / "wgc.md").write_text("整合 WGC", encoding="utf-8")
    path = tmp_path / "master.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path, raw


def test_valid_master_has_no_errors(tmp_path):
    path, raw = write_master(tmp_path, master())

    assert validate_file(path, SCHEMA, raw) == []


def test_schema_violation_is_reported_with_its_location(tmp_path):
    data = master()
    del data["experience"][0]["company"]
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw)

    assert len(errors) == 1
    assert errors[0].startswith("experience/0:") and "company" in errors[0]


def test_source_file_missing_from_raw_dir_is_reported(tmp_path):
    data = master()
    data["experience"][0]["achievements"][0]["sources"][0]["file"] = "wiki/gone.md"
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw)

    assert len(errors) == 1
    assert "wgc-capture" in errors[0] and "wiki/gone.md" in errors[0]


def test_duplicate_achievement_ids_are_reported(tmp_path):
    data = master()
    first = data["experience"][0]["achievements"][0]
    data["projects"] = [{"id": "p1", "name": "P1", "achievements": [dict(first)]}]
    path, raw = write_master(tmp_path, data)

    errors = validate_file(path, SCHEMA, raw)

    assert len(errors) == 1
    assert "duplicate" in errors[0] and "wgc-capture" in errors[0]
