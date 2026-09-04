# Encoding the tree on TaskCreate/TaskUpdate

The harness's task graph already gives you a dependency DAG (`addBlocks` /
`addBlockedBy`) and a free-form `metadata` bag per task. That's enough to represent
the whole tree — root, branches, leaves — plus the five-state lifecycle. Don't
build a parallel tracking system; extend the task graph with metadata instead.

## The five states, mapped onto the tool's real fields

The tool natively has `status: pending | in_progress | completed | deleted` plus
`blockedBy`. That's not quite the five states the tree needs, so here's the mapping:

| Conceptual state | How it looks in the task graph |
|---|---|
| WAITING   | `status: pending`, `blockedBy` non-empty |
| READY     | `status: pending`, `blockedBy` empty, no `owner` |
| IN-FLIGHT | `status: in_progress`, `owner` set to the dispatch (e.g. the worktree branch name) |
| VERIFIED  | `status: completed`, `metadata.state == "VERIFIED"` |
| ABANDONED | `status: completed`, `metadata.state == "ABANDONED"`, `metadata.abandon_reason` set |

The important discipline: **never set `status: completed` without also setting
`metadata.state`.** A bare `completed` with no `metadata.state` is ambiguous — did
you verify it, or just stop working on it? Treat any task like that as not-done and
fix its metadata before trusting it. This is also why you can't just ask "is
everything `completed`?" to check for done — you must check `metadata.state` too.

## metadata fields to set

On every task (root, branch, or leaf):

- `node_type`: `"root" | "branch" | "leaf"`
- `requirement`: the piece of the user's contract this task exists to satisfy, in
  plain words — this is what lets you answer "which requirement is still blocking
  completion?" by reading the task list, and what lets you tell whether a
  requirement has silently gone untracked.

On leaves specifically:

- `difficulty`: `"easy" | "medium" | "hard"` — set when you create the leaf; drives
  which model you dispatch it to (haiku/sonnet/opus — see SKILL.md).
- `owner_paths`: array of file/directory globs this leaf is allowed to touch. Two
  leaves dispatched in the same parallel wave must have disjoint `owner_paths`.
- `gates`: the leaf's acceptance gates, as an array of `{id, check, expect}`. Keep
  this in the task description if it's easier to read there — metadata is fine for
  small structured data, the description field is fine for the human-readable
  version; do whichever keeps it legible, they don't have to be redundant.
- `attempt_count`: increment each time you (re)dispatch this leaf. Use it to decide
  when to escalate model tier or give up and abandon (see SKILL.md's failure
  handling section).
- `worktree_branch`: the branch name from the most recent dispatch, so you know what
  to merge.

On a task once it reaches a terminal state:

- `state`: `"VERIFIED" | "ABANDONED"` (see table above)
- `evidence` (VERIFIED only): a short record of what you last actually ran and saw —
  the gate command and enough of its output to trust the result later without
  re-running it, e.g. `"ran: npm test -- auth.spec.ts | 12 passed, 0 failed"`.
  This is what lets you tell later whether re-verification is needed: if none of the
  files/dependencies behind that evidence have changed since, you can trust it a
  while longer; if they have, don't — re-run the gate rather than assume the old
  evidence still holds.
- `abandon_reason` (ABANDONED only): why, in enough detail that whoever picks this up
  later (possibly you, next session) doesn't have to rediscover it.

On branch and root tasks specifically:

- `integration_gates`: the gates that prove the children work *together*, not just
  individually (see SKILL.md section 8). Same `{id, check, expect}` shape as leaf
  gates.

## Reading the tree back

`TaskList` gives you `status`, `owner`, `blockedBy` for everything at a glance —
that's your READY/WAITING/IN-FLIGHT picture. Use `TaskGet` on a specific task when
you need its full `metadata` (difficulty, gates, evidence, etc.) before dispatching
or before deciding it's really VERIFIED.

Because this all lives in the task graph rather than a file in the repo, it does not
survive a fresh session by itself — if you need to resume a `/tree` run later, the
task graph from this session is what you're resuming from, so don't let a session
end mid-tree without giving the user an honest status (see SKILL.md's "before you say
done" checklist, and the handoff format if you're stopping incomplete).
