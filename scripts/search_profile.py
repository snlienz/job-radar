"""Search Profile: config/profile.yaml plus per-run `key=value` overrides."""
from pathlib import Path

import yaml

LIST_KEYS = {"include", "exclude", "locations", "industries"}
ALIASES = {"keywords": "include", "location": "locations", "industry": "industries"}
INT_KEYS = {"min_score"}


def load_profile(path: Path | None, overrides: list[str] = ()) -> dict:
    """Return {include, exclude, locations, industries, seniority, min_score}.

    Overrides look like `keywords=firmware,embedded exclude=intern location=Hsinchu min_score=70`
    and replace (not extend) the profile's value for that field.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) if path and Path(path).is_file() else {}
    keywords = raw.get("keywords") or {}
    profile = {
        "include": list(keywords.get("include") or []),
        "exclude": list(keywords.get("exclude") or []),
        "locations": list(raw.get("locations") or []),
        "industries": list(raw.get("industries") or []),
        "seniority": raw.get("seniority"),
        "min_score": int(raw.get("min_score", 0)),
    }
    for item in overrides:
        key, sep, value = item.partition("=")
        key = ALIASES.get(key.strip(), key.strip())
        if not sep or key not in profile:
            raise ValueError(f"bad override {item!r}; expected keywords|exclude|location|industries|seniority|min_score=value")
        if key in LIST_KEYS:
            profile[key] = [v.strip() for v in value.split(",") if v.strip()]
        elif key in INT_KEYS:
            profile[key] = int(value)
        else:
            profile[key] = value.strip()
    return profile
