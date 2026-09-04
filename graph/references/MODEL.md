# Graph data model and resolution rules

## Node shape

```json
{
  "id": "js/store.js::resolveByRecency",
  "type": "function",
  "label": "resolveByRecency",
  "path": "js/sync.js",
  "line": 279,
  "language": "javascript",
  "docstring": "..."
}
```

`id` conventions: a file's id is its repo-relative path (`js/store.js`). A
top-level symbol's id is `path::name` (`js/store.js::save`). A method or
nested function's id is `path::Outer.inner` (`js/store.js::Store.save`,
or for a Python nested function, `path::outer.inner`).

`type` is one of: `file`, `class`, `function`, `method`, `doc`, `external`
(an import target that isn't in this repo), `external_symbol` (a called name
that couldn't be resolved to any definition in this repo), `concept` (a
semantic-layer node, added by hand or by Claude reading docs — not produced
by the extractors).

## Edge shape

```json
{
  "source": "js/app.js",
  "target": "js/store.js",
  "relation": "uses",
  "confidence": "INFERRED",
  "score": 0.85,
  "method": "regex",
  "line": 42
}
```

`relation` is one of: `imports`, `defines`, `calls` (function-granularity,
Python only), `uses` (file-granularity, non-Python languages), `inherits`.
Semantic-layer edges can use any relation name that makes sense for the
concept being described (`explains`, `references`, `implements`, ...).

`method` says how the edge was found: `"ast"` (real parse, Python only),
`"regex"` (heuristic, every other language), or `"semantic"` (Claude read
something and proposed it by hand).

## How confidence gets assigned

This happens in `build_graph.py`'s `assign_confidence_and_resolve`, after all
fragments are merged and a repo-wide symbol table exists. The extractors
themselves never assign confidence — they only record what they saw and how
(`method`), which keeps the two concerns separate: "what happened" vs. "how
sure are we."

**imports** → always `EXTRACTED`, score `1.0`. Whether the source literally
says `import X` or a regex matched the same literal syntax, the statement
existing is not in question — what's uncertain is only whether `X` resolves
to a file in this repo (`target_kind: "internal"`) or not
(`target_kind: "external"`, and a synthetic `external` node gets created for
it). An external target is a completely valid, certain outcome — it does not
lower confidence.

**defines** → `EXTRACTED` (score `1.0`) when `method` is `"ast"`; `INFERRED`
(score `0.85`) when `method` is `"regex"`, because a regex can be fooled by a
commented-out declaration or an unusual formatting style in a way a real
parse cannot.

**calls / uses / inherits** → these carry a `raw_target` (a bare symbol name)
that has to be resolved against the repo-wide symbol index
(`build_symbol_index`: simple name → every function/method/class node with
that label):

- **Exactly one match** → `INFERRED`. Base score `0.9` for an `"ast"`-sourced
  edge, `0.75` for `"regex"`-sourced (regex has a higher false-positive rate
  going in, so even a clean single-match resolution stays a bit more
  cautious). If the match lands in the same file as the call site, add `0.05`
  (capped at `0.95`) — same-file resolution has less room for a same-named
  decoy elsewhere in a large repo.
- **Zero matches** → `AMBIGUOUS`, `score: null`, `reason: "no matching
  definition found in this graph"`. Almost always an external library/stdlib
  call. A synthetic `unresolved:<name>` node holds the target so the edge
  still has somewhere to point.
- **More than one match** → `AMBIGUOUS`, `score: null`, `candidates: [...]`
  listing every node id that shares the name. This is a real naming
  collision in the repo — worth actually looking at, not just noise.

Nothing in any of these three outcomes gets silently dropped — an
`AMBIGUOUS` edge is kept in `graph.json`'s `edges` list (not hidden in a
separate discard pile) and also duplicated into `ambiguous_edges` so the
report and `query.py` can both surface it without every consumer having to
filter for it themselves.

## Import target resolution

`resolve_import_target` tries to turn a raw import string into a real file
id, since "this file imports `./utils`" is far more useful once you know
`./utils` means `js/utils.js`, not just a string.

- **Python**: leading dots become relative-import levels (walk up that many
  parent directories from the importing file), remaining dotted segments
  become path segments, then try `<path>.py` and `<path>/__init__.py`.
- **JS/TS-family**: only relative imports (`./x`, `../x`) are resolved —
  a bare `lodash`-style import is assumed to be an external package and isn't
  attempted. Tries `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, and the same
  set again with `/index` appended.
- Anything else (Go, Java, Rust, ...) isn't resolved yet — imports still get
  recorded as `EXTRACTED` facts, just always pointing at an `external` node
  even when the target is technically in-repo. Extending
  `_python_import_candidates`/`_js_import_candidates` in `build_graph.py`
  with an equivalent resolver for another language's import syntax is the
  natural way to improve this.

## Semantic fragment shape (for the doc/concept layer)

A file of semantic fragments passed via `--semantic` is a JSON array, each
entry shaped like an extractor fragment:

```json
[
  {
    "nodes": [{"id": "concept:auth-architecture", "type": "concept", "label": "Auth architecture"}],
    "edges": [
      {"source": "AUTH_ARCHITECTURE.md", "target": "netlify/functions/_lib/auth.js",
       "relation": "explains", "confidence": "INFERRED", "score": 0.8}
    ]
  }
]
```

Referencing an existing file/symbol id as `source` or `target` links straight
into the structural graph; a new `concept:` id creates a standalone concept
node. Set your own `confidence`/`score` honestly — there's no resolver
double-checking a semantic edge the way there is for a raw call, so don't
mark something `EXTRACTED` unless it's a literal citation/link, and use
`AMBIGUOUS` rather than a low-confidence guess dressed up as a score.

## Extending to a real parser for another language

If `tree-sitter` (or a language-specific parser) is genuinely available in a
given environment, the clean extension point is `extract_file()` in
`extract.py`: add a branch that shells out to the real parser for that
extension instead of falling into `extract_js_like`/`extract_generic_code`,
and tag its edges `"method": "ast"` so they get the same confidence treatment
Python's real parse gets. Don't tag a new heuristic `"ast"` just because it
feels more thorough than regex — the tag is a promise to everything
downstream that the fact is real, not guessed.
