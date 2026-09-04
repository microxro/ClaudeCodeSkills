---
name: graph
description: Build and query a persistent, confidence-tagged knowledge graph of a repository (files, classes, functions, imports, calls, inheritance, docs) instead of rediscovering its structure from scratch every time you need codebase context. Use whenever a task needs you to understand how a codebase is put together to do the work well — a code review, "what does this PR touch and depend on", architecture questions ("how does auth connect to the database", "what depends on this service", "what would break if I changed this"), prep before a large refactor, or unfamiliar-codebase exploration — or whenever the user asks to "graph", "map", or "graphify" the repo. If a graph already exists (check .graph/graph.json), query it first and read only the exact files it points to instead of grepping broadly — that saves tokens versus rediscovering structure on every multi-file task. Skip this for a small repo, a single-file task, or a question about what one line of code does — read the file directly instead.
---

# /graph — a persistent map of the repo, so you stop rediscovering it

## What this actually is (read this before promising anything to the user)

This is a scoped-down implementation of the same idea as the public Graphify
project — but a Claude Code skill can't spin up a standalone server, bundle
tree-sitter grammars for thirty languages, or run a real Leiden clustering
library, so don't describe this skill in those terms. Here's what's real and
what's simplified, honestly:

- **Python gets a real AST parse** (`ast`, stdlib, always available) — imports,
  classes, functions, methods, inheritance, and calls are structural facts,
  not guesses.
- **Every other language gets regex-based heuristic extraction** — good enough
  to find imports, top-level classes/functions, and file-level "this file
  calls something named X somewhere," but it is not a real parse and every
  edge it produces is tagged `"method": "regex"` so nothing downstream
  pretends otherwise.
- **God nodes are real** — plain degree centrality (how many edges touch a
  node), computed directly, no approximation.
- **Communities are real but simpler than Graphify's** — label propagation
  (Raghavan et al.), a legitimate community-detection algorithm implementable
  in pure Python, standing in for Graphify's Leiden clustering. It finds
  genuinely similar structural groupings; it's just a lighter algorithm.
- **No MCP server, no HTTP transport, no PR triage, no git hooks, no
  multimodal (PDF/image/video) extraction.** If the user wants the graph
  updated automatically on every commit, that's a manual `--update` re-run
  you'd need to wire into their own git hook — don't claim it happens on its
  own.

If you're ever unsure whether to describe something as automatic or as
something you'd need to set up, say the honest, more modest version. That's
the whole point of a confidence-tagged graph — don't undermine it by being
vague about the tool that built it.

## The idea

```
Without a graph:                      With a graph:
question                              question
  -> grep across the repo               -> query graph.json for the region that matters
  -> open a dozen files                 -> open the handful of files it points to
  -> infer how they connect             -> read them with the connections already known
  -> repeat next question               -> next question starts from structure, not zero
```

The graph doesn't replace reading source — it tells you which source is worth
reading first. Map, then terrain, every time: query before you grep broadly,
then always verify anything load-bearing against the real file, especially
before editing it.

## When to build/use one

Worth it any time doing the task well requires actually understanding how
the codebase fits together, not just reading the one file in front of you:
a **code review** (what does this change actually touch, what depends on the
code being reviewed, does it fit the surrounding module's conventions), an
**architecture question** ("what actually calls this", "how does X reach Y",
"what would a change to this file ripple into"), or prep before a **refactor**
that touches several files. Anywhere you'd otherwise burn tokens grepping
across a dozen-plus files just to build a mental model before you can even
start the real task, the graph is meant to replace that step. Not worth it
for a small repo you can hold in your head, a single-file change, or "what
does this specific function return" — that's faster to just read.

There's a global SessionStart hook (see `scripts/session_start_hook.py`,
wired up in `~/.claude/settings.json`) that already does the "does a graph
exist / is it fresh / should I build one" check automatically at the start
of any session in a git repo with enough source files to be worth it — if
it ran, you'll see a context note saying so. If you don't see that note (a
smaller repo, or the hook isn't installed in this environment), decide for
yourself using the criteria above rather than assuming no graph is wanted.

## Build or update the graph

```
python3 scripts/build_graph.py <repo_root> --out-dir .graph
```

Writes `.graph/graph.json` (the persistent graph), `.graph/GRAPH_REPORT.md`
(human-readable summary — god nodes, communities, ambiguous edges worth a
look, extraction errors), and `.graph/graph.html` (a self-contained,
offline-capable visualization — open it in a browser, drag nodes, click one
to highlight its neighborhood).

Once a graph already exists, refresh it incrementally rather than rebuilding
from scratch — it only re-extracts files whose content actually changed:

```
python3 scripts/build_graph.py <repo_root> --out-dir .graph --update
```

Respects `.gitignore` and an optional `.graphignore` (same syntax) in the
repo root automatically.

## Query it

```
python3 scripts/query.py <repo_root> stats
python3 scripts/query.py <repo_root> search "auth"
python3 scripts/query.py <repo_root> neighbors "AuthService"
python3 scripts/query.py <repo_root> explain "AuthService"
python3 scripts/query.py <repo_root> path "LoginController" "DatabasePool"
```

`neighbors`/`explain`/`path` accept a search string, not just an exact node
id — if it matches more than one node, you'll get a candidate list back
instead of a guess, so be more specific rather than assuming which one was
meant. `stats` is the fastest way to get oriented in an unfamiliar repo: the
god-node list alone usually tells you where the real architecture lives.

**The actual workflow that makes this worth doing:** before grepping broadly
for a structural question, a code review, or any task that needs you to
understand how a change relates to the rest of the codebase, check whether
`<repo_root>/.graph/graph.json` exists. If it does (and isn't obviously stale
— check whether recent commits touched a lot of ground since it was last
built), query it first. Use what it returns to go straight to the handful of
files that matter, instead of casting a wide net. If no graph exists and the
repo is large enough to justify one, offer to build it before diving in — it
pays for itself the moment there's a second question, and a review is
usually not the last question you'll be asked about that code.

## Reading the confidence tags

Every edge is one of three things, and they mean different things depending
on which extraction path produced them — read `references/MODEL.md` for the
full resolution rules, but the short version:

- **EXTRACTED** — a literal structural fact: an import statement exists, a
  function/class is defined here. Trust it.
- **INFERRED** (0.75–0.95) — a call or inheritance relationship that got
  resolved by matching a name against the repo's real symbol table. Higher
  score means less naming ambiguity going into the match. Treat it as
  probably right, not certain — verify before it drives a consequential
  decision.
- **AMBIGUOUS** — kept, not dropped, specifically so nothing silently
  disappears: either the name matched zero definitions (probably an external
  library call) or matched more than one (a real naming collision in the
  repo worth knowing about). Don't treat these as facts.

One asymmetry worth internalizing: **Python's call/inherit edges resolve at
function granularity** (a real AST knows exactly which function a call sits
inside), while **every other language's call-style edges resolve at file
granularity** (regex extraction can't reliably track function boundaries, so
"this file uses X somewhere" is as precise as it gets). Don't present a
JS/Go/Ruby/etc. "uses" edge as if it pinpoints the calling function — it
doesn't, and the report/query output labels it `uses` rather than `calls` for
exactly this reason.

## Adding the semantic layer (optional, and it's your job, not a script's)

Structural extraction can't know that `AuthService` is coupled to a decision
documented in `AUTH_ARCHITECTURE.md`, or that a diagram explains a concept
also implemented in three files. That's for you to find by actually reading
docs/READMEs/comments and proposing graph fragments in the same
node/edge shape the extractor uses — nodes for concepts, edges tagged
`"method": "semantic"` with your own honest `INFERRED` score or `AMBIGUOUS`
if you're genuinely unsure. Save them as JSON (see `references/MODEL.md` for
the exact shape) and merge them in:

```
python3 scripts/build_graph.py <repo_root> --out-dir .graph --semantic fragments.json
```

For a large corpus, splitting this across a handful of parallel subagents
(one per doc or module) keeps it fast — same principle as any other
decompose-and-parallelize task, just applied to reading docs instead of
writing code.

## God nodes and communities

God nodes (top of `GRAPH_REPORT.md`, also `query.py stats`) are the
highest-degree nodes in the graph — the files/symbols a large share of
everything else touches. They're where architecture actually concentrates,
and where a change is most likely to ripple. Treat a high-degree node as a
signal to slow down before editing it, not just a trivia fact.

Communities are structural clusters — nodes more connected to each other than
to the rest of the graph. They usually correspond to real subsystems even
though nothing told the algorithm what a "subsystem" is; if a community's
membership looks like an obvious single concern (all the shop-related
functions, all the auth-related functions), that's the graph doing its job.
If a community looks arbitrary, don't force meaning onto it — label
propagation is a decent heuristic, not a guarantee.

## Keeping it fresh

The graph goes stale the moment source changes and nobody re-runs it — there
is no hook doing this automatically. After a meaningful batch of edits (not
every single save), re-run with `--update`. If you're about to answer an
architecture question and the graph's `meta.generated_at` looks old relative
to recent commit activity, say so and offer to refresh it rather than
answering from a graph you know might be wrong.

For the exact node/edge schema, the full confidence-resolution rules, and how
import-target resolution works per language, see `references/MODEL.md`.
