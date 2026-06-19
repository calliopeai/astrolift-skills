#!/usr/bin/env python3
"""Validate the skills catalogue (run by CI and locally).

Two checks, both stdlib-only:

1. **Frontmatter** — every ``skills/*/SKILL.md`` parses and carries a
   non-empty ``name`` + ``description`` (the keys the platform loader
   treats as required), and a non-empty markdown body.
2. **Drift** — ``catalogue.json`` matches what ``gen_catalogue.py`` would
   produce right now, so the committed index can never silently rot.

Reuses the parser in :mod:`gen_catalogue` so validation and generation
can never disagree about what "valid frontmatter" means.

Exit code 0 = all good; 1 = one or more problems (printed to stderr).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_catalogue import (  # noqa: E402  (import after sys.path tweak)
    CATALOGUE_PATH,
    REPO_ROOT,
    SKILLS_DIR,
    SkillParseError,
    build_catalogue,
    render_catalogue,
    split_frontmatter,
)


def _validate_one(skill_md: Path) -> list[str]:
    """Return a list of problems for one SKILL.md (empty == valid)."""
    rel = skill_md.relative_to(REPO_ROOT).as_posix()
    problems: list[str] = []
    try:
        text = skill_md.read_text(encoding="utf-8")
        front, body = split_frontmatter(text)
    except (OSError, SkillParseError) as exc:
        return [f"{rel}: {exc}"]

    # Reuse the canonical loader for the required-key checks.
    try:
        from gen_catalogue import parse_frontmatter

        meta = parse_frontmatter(front)
    except SkillParseError as exc:
        return [f"{rel}: {exc}"]

    for key in ("name", "description"):
        if not meta.get(key):
            problems.append(f"{rel}: missing or empty required frontmatter key {key!r}")
    if not body.strip():
        problems.append(f"{rel}: empty instruction body")
    return problems


def validate_frontmatter() -> list[str]:
    """Validate every skill's frontmatter; return all problems found."""
    if not SKILLS_DIR.is_dir():
        return [f"skills directory not found: {SKILLS_DIR}"]
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        return [f"no SKILL.md files found under {SKILLS_DIR}"]
    problems: list[str] = []
    for skill_md in skill_files:
        problems.extend(_validate_one(skill_md))
    return problems


def validate_catalogue_in_sync() -> list[str]:
    """Confirm catalogue.json matches a fresh generation; return problems."""
    expected = render_catalogue(build_catalogue())
    if not CATALOGUE_PATH.exists():
        return ["catalogue.json is missing — run `python scripts/gen_catalogue.py`"]
    current = CATALOGUE_PATH.read_text(encoding="utf-8")
    if current != expected:
        return ["catalogue.json is out of date — run `python scripts/gen_catalogue.py`"]
    return []


def main() -> int:
    problems = validate_frontmatter()
    problems += validate_catalogue_in_sync()

    if problems:
        print("Skill catalogue validation FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    count = len(sorted(SKILLS_DIR.glob("*/SKILL.md")))
    print(f"Skill catalogue OK: {count} skills, frontmatter valid, catalogue.json in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
