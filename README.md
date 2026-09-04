# skills_of_claude

Portable [Claude Code](https://claude.com/claude-code) skills — clone this repo
on any machine to install them.

## What's here

- **`tree/` — `/tree`**: decompose a large or multi-part build into a verified
  task tree, dispatch independent pieces to parallel subagents (model-tiered —
  opus for hard work, sonnet for standard implementation, haiku for
  boilerplate), and refuse to declare it done until every piece is
  implemented, self-tested by its own worker, re-verified against the merged
  code, and integration-checked together.

- **`taste/` — `/taste`**: apply practitioner judgment instead of
  generic-model defaults when creating or critiquing anything real — ground
  in the actual job/audience/exemplar, choose the right shape, rank by
  impact, use only source-backed specifics, commit to one recommendation,
  then subtract and quality-gate. Includes domain guidance for code, UI,
  documents, data, systems, and app/site deployment (with reference
  checklists for App Store, Play Store, and Vercel submission).

- **`graph/` — `/graph`**: build and query a persistent, confidence-tagged
  knowledge graph of a repository (files, classes, functions, imports,
  calls, inheritance) instead of rediscovering its structure from scratch on
  every question — real AST parsing for Python, honestly-labeled heuristic
  extraction for other languages, god-node/community detection, a
  self-contained HTML visualization, and an optional SessionStart hook to
  keep it built automatically.

Each skill is a standard `SKILL.md` (+ `references/`, and for `graph/`,
`scripts/`) — nothing here depends on the others, install any subset.

## Install

Clone the repo, then either run the installer or copy the folders by hand.

```bash
git clone <this-repo-url>
cd ClaudeCodeSkills
./install.sh                              # -> ~/.claude/skills (personal, every project)
./install.sh /path/to/project/.claude/skills   # -> a single project instead
```

Or by hand:

```bash
cp -r tree taste graph ~/.claude/skills/
```

That's it — no build step, no dependencies beyond Python 3 (stdlib only,
used by `/graph`'s scripts) and `git`. New Claude Code sessions will see
`/tree`, `/taste`, and `/graph` in their skill list.

### Optional: `/graph`'s auto-build hook

`graph/scripts/session_start_hook.py` will, if wired into
`~/.claude/settings.json` as a `SessionStart` hook, automatically build or
refresh a repo's knowledge graph at the start of any session in a git repo
with enough source files to be worth it, and tell the session to consult it
before broad grepping. This is opt-in and not registered by `install.sh` —
see the snippet it prints at the end, or `graph/SKILL.md`, for the exact
`settings.json` stanza to add.

## Updating

Pull the latest version of this repo, then re-run `install.sh` — it
overwrites the previous copy of each skill directory.

## License

MIT — see [LICENSE](LICENSE).
