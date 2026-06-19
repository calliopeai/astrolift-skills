#!/usr/bin/env python3
"""Generate ``catalogue.json`` from the ``skills/*/SKILL.md`` set.

The catalogue is the discovery index for the built-in Astrolift skills
baseline (spec 39). It powers bare-name resolution (``"http-request"`` ->
``skills/http-request``) and a future "browse skills" UI.

Each skill is a folder under ``skills/`` containing an agentskills.io
``SKILL.md``: YAML frontmatter delimited by ``---`` fences with required
``name`` + ``description`` keys (and an optional ``version``), followed by
the markdown instruction body. This script reads only the frontmatter.

We parse the frontmatter with a tiny dependency-free reader rather than
pulling in PyYAML so the generator (and the CI that runs it) stays
stdlib-only. The frontmatter we author is intentionally a flat
``key: value`` block, which is the subset this reader supports.

Usage::

    python scripts/gen_catalogue.py            # write catalogue.json
    python scripts/gen_catalogue.py --check     # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CATALOGUE_PATH = REPO_ROOT / "catalogue.json"

# Frontmatter keys we surface in the catalogue, in emit order per entry.
_REQUIRED_KEYS = ("name", "description")


class SkillParseError(ValueError):
    """Raised when a SKILL.md is missing or has malformed frontmatter."""


def split_frontmatter(text: str) -> tuple[str, str]:
    """Split a SKILL.md into (frontmatter_block, body).

    The frontmatter is the block between a leading ``---`` line and the
    next ``---`` line, mirroring agentskills.io / Jekyll front matter.
    Raises :class:`SkillParseError` if the opening or closing fence is
    absent.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillParseError("missing opening '---' frontmatter fence")
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            front = "\n".join(lines[1:idx])
            body = "\n".join(lines[idx + 1 :])
            return front, body
    raise SkillParseError("missing closing '---' frontmatter fence")


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(block: str) -> dict[str, str]:
    """Parse a flat ``key: value`` frontmatter block into a dict.

    Supports the subset we author: one ``key: value`` per line, optional
    surrounding quotes on the value, ``#`` comment lines, and blank lines.
    Nested structures are deliberately unsupported — the catalogue's
    frontmatter is flat by design, which keeps both this reader and the
    platform loader simple.
    """
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise SkillParseError(f"frontmatter line is not 'key: value': {raw!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            raise SkillParseError(f"empty frontmatter key in line: {raw!r}")
        out[key] = _strip_quotes(value)
    return out


def load_skill(skill_md: Path) -> dict[str, str]:
    """Read one SKILL.md and return its frontmatter as a dict.

    Validates that the required keys are present and non-empty so the
    platform loader (which treats ``name`` + ``description`` as required)
    will accept it.
    """
    text = skill_md.read_text(encoding="utf-8")
    front, _ = split_frontmatter(text)
    meta = parse_frontmatter(front)
    for key in _REQUIRED_KEYS:
        if not meta.get(key):
            raise SkillParseError(f"{skill_md}: missing required frontmatter key {key!r}")
    return meta


def build_catalogue(skills_dir: Path = SKILLS_DIR) -> list[dict[str, str]]:
    """Scan ``skills/*/SKILL.md`` and return the catalogue list.

    Each entry is ``{name, description, version, path}``. ``version``
    defaults to an empty string when the skill omits it. Entries are
    sorted by ``name`` for a stable, diff-friendly index.
    """
    if not skills_dir.is_dir():
        raise SkillParseError(f"skills directory not found: {skills_dir}")

    entries: list[dict[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        meta = load_skill(skill_md)
        rel = skill_md.parent.relative_to(REPO_ROOT).as_posix()
        entries.append(
            {
                "name": meta["name"],
                "description": meta["description"],
                "version": meta.get("version", ""),
                "path": rel,
            }
        )
    entries.sort(key=lambda e: e["name"])
    return entries


def render_catalogue(entries: list[dict[str, str]]) -> str:
    """Render the catalogue list to its canonical JSON text (trailing NL)."""
    return json.dumps(entries, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify catalogue.json is up to date; exit 1 if it would change",
    )
    args = parser.parse_args(argv)

    entries = build_catalogue()
    rendered = render_catalogue(entries)

    if args.check:
        current = CATALOGUE_PATH.read_text(encoding="utf-8") if CATALOGUE_PATH.exists() else ""
        if current != rendered:
            print(
                "catalogue.json is out of date — run `python scripts/gen_catalogue.py`",
                file=sys.stderr,
            )
            return 1
        print(f"catalogue.json is up to date ({len(entries)} skills)")
        return 0

    CATALOGUE_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {CATALOGUE_PATH.relative_to(REPO_ROOT)} ({len(entries)} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
