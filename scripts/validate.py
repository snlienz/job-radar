"""Validate a resume YAML file against its JSON schema."""
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def _achievements(data: dict):
    for section in ("experience", "projects"):
        for entry in data.get(section, []):
            yield from entry.get("achievements", [])


def _normalize(text: str) -> str:
    """Collapse whitespace runs: extraction may change line breaks."""
    return re.sub(r"\s+", " ", text).strip()


def _source_text(rel: str, raw_dir: Path, extracted_dir: Path) -> str | None:
    extracted = extracted_dir / (rel + ".txt")
    if extracted.is_file():
        return extracted.read_text(encoding="utf-8")
    raw = raw_dir / rel
    if raw.suffix.lower() in (".md", ".txt"):
        return raw.read_text(encoding="utf-8")
    return None


def _check_provenance(data: dict, raw_dir: Path, extracted_dir: Path) -> list[str]:
    errors = []
    seen = set()
    texts: dict[str, str | None] = {}
    for ach in _achievements(data):
        if ach["id"] in seen:
            errors.append(f"duplicate achievement id: {ach['id']}")
        seen.add(ach["id"])
        for source in ach.get("sources", []):
            if not (raw_dir / source["file"]).is_file():
                errors.append(
                    f"achievement {ach['id']}: source file not found in raw dir: {source['file']}"
                )
                continue
            rel = source["file"]
            if rel not in texts:
                text = _source_text(rel, raw_dir, extracted_dir)
                texts[rel] = None if text is None else _normalize(text)
            if texts[rel] is None:
                errors.append(
                    f"achievement {ach['id']}: no extracted text for {rel} "
                    f"(run scripts/extract.py), cannot check quote"
                )
            elif _normalize(source["quote"]) not in texts[rel]:
                errors.append(
                    f"achievement {ach['id']}: quote not found verbatim in {rel}: "
                    f"{source['quote'][:40]!r}"
                )
    for skill in data.get("skills", []):
        for ref in skill.get("evidence", []):
            if ref not in seen:
                errors.append(f"skill {skill['name']}: evidence id not found: {ref}")
    return errors


def validate_file(
    yaml_path: Path, schema_path: Path, raw_dir: Path, extracted_dir: Path
) -> list[str]:
    data = yaml.safe_load(Path(yaml_path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in Draft202012Validator(schema).iter_errors(data)
    ]
    if errors:  # provenance checks assume a structurally valid file
        return errors
    return _check_provenance(data, Path(raw_dir), Path(extracted_dir))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schemas/master.schema.json"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--extracted", type=Path, default=Path("data/extracted"))
    args = parser.parse_args()

    errors = validate_file(args.yaml_path, args.schema, args.raw, args.extracted)
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print(f"{args.yaml_path}: OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
