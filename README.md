# astrolift-skills

The **built-in skills catalogue** for [Astrolift](https://github.com/calliopeai) —
the baseline set of agent skills that ships with every Astrolift deployment so a
fresh install has useful "batteries" with zero setup.

A *skill* is a reusable unit of instructions (plus optional helper scripts) that
an agent receives at boot. This repo curates the common-case skills in the
[agentskills.io](https://agentskills.io) format. It is the lowest-precedence of
the three skill sources defined in
[spec 39](https://github.com/calliopeai/astrolift-spec) — a **bare name** like
`"http-request"` resolves here.

## The format (agentskills.io)

Each skill is a folder under `skills/<name>/` containing a required `SKILL.md`:

```markdown
---
name: http-request
description: Make HTTP/REST requests with auth, retries, pagination, and error handling.
version: "0.1.0"
---

# http-request

<markdown instructions an agent follows…>
```

- **YAML frontmatter** fenced by `---`. `name` and `description` are **required**;
  `version` is optional (semver string). Extra keys are allowed and ignored by the
  catalogue.
- **Markdown body** — the actual procedural instructions the agent reads.
- Optional sibling folders:
  - `scripts/` — executable helpers the agent can call (Python preferred, stdlib
    first; any non-stdlib dependency is named in the SKILL.md so the runner can
    install it).
  - `references/` — supporting docs the agent can open on demand.
  - `assets/` — templates, fixtures, or other files the skill ships.

The frontmatter is a **flat `key: value` block** by design — that keeps both the
catalogue generator and the platform loader (`astrolift_manifest`) dependency-free.

## How skills are referenced (GitHub-Actions-style)

Skills are referenced from an agent's `skills = [ … ]` list much like `uses:` in
GitHub Actions. A reference resolves against three sources, most-specific first:

| Form | Source | Meaning |
|---|---|---|
| `"http-request"` | built-in catalogue | this repo, latest bundled |
| `"http-request@0.1.0"` | built-in catalogue | this repo, pinned version |
| `"./skills/foo"` or `{ name = "./skills/foo" }` | local | a folder in the agent's own repo |
| `"acme/dev-skills/pr-review@v2"` | org repo | `<repo-alias>/<skill-path>@<ref>` |

Precedence when a bare name could match several: **local repo skill → org repo →
built-in catalogue**. Resolution is logged, so it is never silent. Pinning (`@ref`)
works on catalogue and org-repo refs (a tag/branch/sha), mirroring
`actions/checkout@v4`; local skills are pinned implicitly by the agent's commit.

## `catalogue.json`

A generated discovery index — one entry per skill, sorted by name:

```json
[
  { "name": "csv-process", "description": "…", "version": "0.1.0", "path": "skills/csv-process" }
]
```

It powers bare-name resolution and a future "browse skills" UI. It is committed
and **kept in sync by CI** — regenerate it with:

```bash
python scripts/gen_catalogue.py          # rewrite catalogue.json
python scripts/gen_catalogue.py --check   # exit 1 if it would change
```

## Adding a skill

1. Create `skills/<name>/SKILL.md` with the required frontmatter and a focused,
   genuinely useful instruction body.
2. Add a `scripts/` helper only where it clearly saves the agent work. Keep it
   stdlib-first; note any extra dependency in the SKILL.md (e.g. `requests`,
   `pandas`). Helpers must byte-compile cleanly.
3. Regenerate the index: `python scripts/gen_catalogue.py`.
4. Validate before opening a PR: `python scripts/validate_skills.py`.

**Guiding rule for what belongs here:** common things an agent should *just know
how to do*, not look up each time. This is the foundational baseline every
deployment ships — keep each skill focused and real.

## v0.1 starter set

The locked v0.1 baseline (spec 39) — the foundational batteries:

| Skill | What it does |
|---|---|
| `http-request` | REST/HTTP client: auth, headers, query/body, pagination, retries, error handling |
| `mcp-client` | Connect to an MCP server; discover and invoke its tools |
| `shell` | Run shell commands safely — quoting, exit codes, output capture, timeouts |
| `file-ops` | Read/write/search/edit files in the workspace |
| `data-transform` | jq-style select / filter / reshape over JSON & YAML |
| `git` | Clone / branch / diff / commit / push basics |
| `csv-process` | Read / filter / aggregate / join / transform CSV |
| `pdf-generate` | "Print to PDF": render markdown / HTML / a report to PDF |
| `export` | Write a dataset to CSV / JSON / XLSX / PDF through one interface |

More skills (workflows and the rest of the data/docs tier) are added in later
passes as we build and test against real agents.

## Repo layout

```
astrolift-skills/
  README.md                     this file
  AGENTS.md / CLAUDE.md         agent shims -> README
  catalogue.json                generated discovery index (committed)
  scripts/
    gen_catalogue.py            build catalogue.json from skills/*/SKILL.md
    validate_skills.py          frontmatter + drift validation (run by CI)
  skills/
    <name>/SKILL.md (+ scripts/ where useful)
  .github/workflows/validate.yml  CI: validate frontmatter + catalogue drift
```

## License

See [`LICENSE`](./LICENSE).
