from pathlib import Path

import yaml

from stories import new_achievements, numbers, validate_stories

SCHEMA = Path(__file__).parent.parent / "schemas" / "stories.schema.json"


def master_data():
    return {
        "basics": {"name": "Steven Lien"},
        "experience": [
            {
                "id": "barco",
                "company": "Barco",
                "title": "Software Engineer",
                "period": {"start": "2019-03", "end": "present"},
                "achievements": [
                    {
                        "id": "cv-speedup",
                        "text": "Sped up template matching for Teams detection.",
                        "metrics": ["Scan time 15 s -> 2 s", "Over 1700 golden sample images"],
                        "sources": [],
                    },
                    {"id": "flicker-fix", "text": "Fixed a capture flicker reported by 9 testers.", "sources": []},
                    {"id": "secret", "text": "Private work.", "tags": ["do-not-use"], "sources": []},
                ],
            }
        ],
    }


def bank(**overrides):
    story = {
        "id": "detection-speed",
        "title": "Making Teams detection fast enough to ship",
        "themes": ["technical-challenge"],
        "achievements": ["cv-speedup"],
        "situation": "In 2019 our Teams detection was too slow.",
        "task": "Make template matching fast enough for production.",
        "action": "Built a dataset of 1,700 images and profiled the scan.",
        "result": "Scan time fell from 15 s to 2 s.",
        "reflection": "I would profile first next time, it took 3 weeks to find.",
    }
    story.update(overrides)
    return {"built_from": ["cv-speedup", "flicker-fix", "secret"], "stories": [story]}


def check(tmp_path, data, master=None):
    master_path = tmp_path / "master.yaml"
    master_path.write_text(yaml.safe_dump(master or master_data()), encoding="utf-8")
    path = tmp_path / "stories.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return validate_stories(path, SCHEMA, master_path)


def test_valid_story_bank_has_no_errors(tmp_path):
    assert check(tmp_path, bank()) == []


def test_story_without_achievements_is_rejected(tmp_path):
    errors = check(tmp_path, bank(achievements=[]))

    assert len(errors) == 1
    assert errors[0].startswith("stories/0/achievements:")


def test_dangling_achievement_id_is_rejected(tmp_path):
    errors = check(tmp_path, bank(achievements=["cv-speedup", "gone"]))

    assert errors == ["story detection-speed: achievement gone not found in master"]


def test_do_not_use_achievement_is_rejected(tmp_path):
    errors = check(tmp_path, bank(achievements=["cv-speedup", "secret"]))

    assert errors == ["story detection-speed: achievement secret is tagged do-not-use"]


def test_number_not_in_a_cited_achievement_is_rejected(tmp_path):
    errors = check(tmp_path, bank(result="Scan time fell from 15 s to 1.5 s."))

    assert errors == ["story detection-speed: result states 1.5, which no cited achievement has"]


def test_number_from_an_uncited_achievement_is_rejected(tmp_path):
    errors = check(tmp_path, bank(result="Scan time fell from 15 s to 2 s; all 9 testers agreed."))

    assert errors == ["story detection-speed: result states 9, which no cited achievement has"]


def test_reflection_numbers_are_not_checked(tmp_path):
    assert check(tmp_path, bank(reflection="It took 12 weeks.")) == []


def test_numbers_ignore_thousands_separators_and_leading_zeros():
    assert numbers("1,700 images in 03/2019, 0.5 s") == {"1700", "3", "2019", "0.5"}


def write_files(tmp_path, built_from):
    master_path = tmp_path / "master.yaml"
    master_path.write_text(yaml.safe_dump(master_data()), encoding="utf-8")
    stories_path = tmp_path / "stories.yaml"
    if built_from is not None:
        stories_path.write_text(yaml.safe_dump({"built_from": built_from, "stories": []}), encoding="utf-8")
    return stories_path, master_path


def test_no_story_bank_is_reported_as_none(tmp_path):
    assert new_achievements(*write_files(tmp_path, None)) is None


def test_bank_missing_new_master_ids_is_stale(tmp_path):
    assert new_achievements(*write_files(tmp_path, ["cv-speedup"])) == ["flicker-fix", "secret"]


def test_bank_built_from_every_master_id_is_current(tmp_path):
    assert new_achievements(*write_files(tmp_path, ["cv-speedup", "flicker-fix", "secret", "removed"])) == []
