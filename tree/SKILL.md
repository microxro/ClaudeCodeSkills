---
name: tree
description: Decompose a large or multi-part build into a verified task tree, splitting it the optimal amount — wide enough to parallelize, never wider than the work actually supports — so it gets done at the best effort in the least wall-clock time, dispatch the independent pieces to parallel subagents (model-tiered — opus for hard/architectural work, sonnet for standard implementation, haiku for boilerplate), and refuse to declare the task done until every required piece has been implemented, self-tested by its own worker, re-verified by you against the merged code, and integration-checked together. Use this whenever a request involves multiple features, multiple components/files, or phrases like "build the whole thing", "make sure everything works", "don't stop until it's done", "run these in parallel" or "use multiple agents" — even if the user never says "skill" or "task tree". Also use whenever the user explicitly invokes /tree. Do NOT use it for a single small fix or one-file change — the decomposition and gate overhead only pays off on real multi-part work.
---

# /tree — decompose, verify, parallelize

## The one idea underneath everything here

An agent finishing a big task naturally drifts toward: implement most of it, run a
couple of checks, feel good about it, say "done." The gap between "I wrote the code"
and "this was actually verified to work, together, right now" is where bugs hide and
users get burned.

This skill closes that gap with one rule:

> **A piece of work is complete only when a gate you just executed says so — not
> because a worker claims it, and not because it passed yesterday.**

Everything below — the tree, the states, the parallel dispatch, the merges — exists
to make that rule practical on tasks too big to hold in your head at once.

The other constant underneath the mechanics: split the work the *optimal* amount, not
the maximal amount. The tree should be exactly as wide as the task's genuinely
independent, disjoint-file, separately-gatable pieces make it — no narrower, which
throws away parallelism and wall-clock speed, and no wider, which spends
dispatch/gate/merge overhead you don't get back. Section 2 below spells out how to
find that width; hold it in mind through the whole workflow, since it's what turns
"decomposed" into "decomposed to finish at the best effort in the least time."

## When to actually use the full machinery

Use it for real multi-part work: a feature with several independently-buildable
pieces, a build touching multiple files/modules, anything where you'd naturally
create more than ~3 todo items. Skip it for a single bug fix or a one-file change —
just do the work and verify it directly; building a tree for a two-line fix is
theater, not discipline.

## The workflow

```
1. Pin the contract        — what is actually required, in the user's words
2. Build the tree          — TaskCreate, root -> branches -> leaves
3. Write gates              — every leaf gets a CHECK + EXPECT
4. Classify difficulty      — each leaf gets easy/medium/hard -> haiku/sonnet/opus
5. Dispatch a wave          — all currently-unblocked leaves, in parallel, isolated
6. Worker implements + self-verifies — runs its own gates before reporting back
7. You merge + re-verify    — never take VERIFIED on the worker's word alone
8. Propagate upward         — branch integration gates, then root gates
9. Repeat 5-8 until nothing is left blocked, ready-but-undispatched, or in-flight
10. Run the completion checklist before you say "done"
```

Steps 5-7 loop: as leaves finish and unblock their dependents, dispatch the newly
unblocked ones immediately rather than waiting for the whole wave (rolling dispatch).
Don't serialize work that doesn't need to be serial.

## 1. Pin the contract

Before decomposing anything, write down — even just in your own head or a task
description — the concrete list of things the user actually asked for. If the user
amends the request mid-task, update this list and treat it as a scope change: new
leaves get added, gates get written for them, and old "done" leaves don't
automatically cover new requirements. A requirement that never gets a leaf and a gate
is a requirement that can silently vanish inside a large project — that's the single
biggest way this kind of task quietly fails.

## 2. Build the tree with TaskCreate

Use the harness's own task graph — `TaskCreate` / `TaskUpdate` / `TaskList` /
`TaskGet` — as the tree. It already gives you the two primitives that matter:
`addBlockedBy`/`addBlocks` for dependencies, and `metadata` for everything the tree
needs that the tool doesn't natively track. Don't build a second, parallel
bookkeeping system — the task graph *is* the depth tree.

Create one task for the root, one per branch, one per leaf. Use `addBlockedBy` to
encode real dependencies (a leaf that needs another leaf's output is blocked by it).
Independent leaves get no `blockedBy` between them — that's what makes them
dispatchable in parallel.

The exact metadata fields to set on each task, and how the five conceptual states
(WAITING / READY / IN-FLIGHT / VERIFIED / ABANDONED) map onto the tool's native
`status` + `blockedBy` + `metadata`, are in `references/state-schema.md`. Read it
before creating tasks — the mapping is simple but you need to get the VERIFIED vs.
plain-`completed` distinction right, since that's the whole point.

A leaf should be a coherent, independently verifiable unit — not "the whole backend,"
not "rename this one variable." If you can't picture a concrete gate for it, it's
still too big or too vague; split it or sharpen it.

**Decompose for width, not just for correctness.** The whole point of dispatching in
parallel is wall-clock time — a tree that's technically correct but mostly a single
chain of `blockedBy` edges gets you almost none of that benefit. Two disciplines,
held at once:

- **Split further wherever files don't overlap.** If a "leaf" is really two
  unrelated concerns living in different files, it's two leaves, not one — don't
  bundle work together just because it's conceptually related if it doesn't have to
  be built in the same pass.
- **Treat every `blockedBy` edge as a claim you have to justify, not a default.**
  Before serializing leaf B after leaf A, ask: does B need A's *actual finished
  code*, or just the *shape* of it (a function signature, a data schema, a response
  format)? If it's the shape, pin that interface yourself, up front, as part of the
  contract — then dispatch A and B in the same wave against the agreed interface, and
  let your integration gate (section 8) catch it later if the real implementations
  don't actually match what was promised. This is usually where the biggest
  parallelism gains are: most "B needs A first" reasoning is really "B needs to know
  what A will look like," which doesn't require A to exist yet.

This is in tension with the no-overlap rule below, not a replacement for it — the
goal is the widest wave you can dispatch *without* two leaves ever claiming the same
file. When those pull against each other, no-overlap wins: two leaves racing on one
file is worse than a slightly narrower wave.

**Optimal is not maximal — stop splitting once a further split stops paying for
itself.** Width is a means to wall-clock speed and independent verifiability, not a
score to maximize. Before adding a split, name what it actually buys:

- **Real parallelism gain** — the two halves can genuinely run concurrently because
  neither blocks on the other's actual output or shape, or
- **Real verifiability gain** — the split piece gets a gate that is meaningfully
  sharper or easier to diagnose than the gate its parent would otherwise need.

If a candidate split buys neither — the two pieces would always be built, gated, and
merged together in practice, or one is too small to justify its own gate, worker
dispatch, and merge overhead — merge it back into its sibling. Two symptoms to watch
for in either direction:

- **Over-split**: leaves so small the dispatch/gate/merge overhead exceeds the work
  itself (e.g. splitting "add a config field" from "read it in the one function that
  uses it" when nothing else touches either), or a wave with far more leaves than the
  task has independently-meaningful pieces.
- **Under-split**: a single leaf quietly doing two or more things that don't share
  files and don't need each other's finished code — the tree looks simple but you've
  thrown away parallelism and made the gate harder to write and diagnose.

There's no fixed number to target — the right count falls out of how many genuinely
independent, disjoint-file, separately-gatable pieces the actual contract has. Re-run
this test on the tree once it's built: for each leaf, could it merge into a neighbor
with no loss of parallelism or gate clarity? If yes, merge it. Could it split further
with a real gain on either axis above? If yes, split it.

## 3. Gates: turn "should work" into "did work, just now"

A gate has two parts:

```
CHECK:  a command you can actually run
EXPECT: what its output/exit code must show for this to count as passing
```

A leaf passes only when you (or, in the first pass, the worker) actually execute
CHECK and confirm EXPECT — not when someone asserts it would pass. Keep gates small
and single-purpose ("valid login creates a session," not "the whole app is
production-ready") — small gates are easier to diagnose, retry, and trust.

Full guidance on writing good gates, avoiding false-green (a gate too weak to catch
the real defect) and false-red (a broken test, not a broken feature), and why you
should never edit a gate just to make it pass, is in `references/gate-design.md`.
Read it before you write gates for anything you haven't gated before — it's short
and it'll save you from the most common failure mode in this whole approach.

## 4. Classify difficulty, pick a model

Every leaf gets a difficulty rating, which picks the model that implements it:

| Difficulty | Model  | Typical leaf |
|---|---|---|
| Hard   | `opus`   | Architecture/design decisions, tricky algorithms, security-sensitive code, ambiguous requirements needing real judgment, anything cross-cutting or an integration gate itself |
| Medium | `sonnet` | Standard feature work — a typical API endpoint, a UI component, a well-specified refactor, most test-writing |
| Easy   | `haiku`  | Boilerplate, scaffolding, config, mechanical renames/formatting, a simple/obvious gate implementation |

Set `metadata.difficulty` when you create the leaf. When you dispatch, pass the
matching `model` to the `Agent` tool. If a leaf keeps failing at its tier after a
genuine fix attempt, escalate it one tier up rather than retrying the same model
forever — repeated failure at the same tier on the same problem is a signal the task
needs more capability, not more attempts.

## 5-6. Dispatch the widest safe wave, with agents that can't step on each other

Two goals, in this priority order: **never let two in-flight leaves touch the same
file**, and **inside that constraint, dispatch as much as is genuinely READY at
once**. The reason parallel agents corrupt each other's work is uncontrolled
concurrent writes to the same files — solve that structurally, not by hoping, and
then use the headroom it buys you:

- **Give every leaf an owner scope** — the files/directories it's allowed to touch
  (`metadata.owner_paths`). Two leaves dispatched in the same wave must have
  disjoint scopes. No exceptions — a leaf that "just needs to peek at" another
  leaf's file gets that information from the pinned interface (see section 2), not
  by reading or touching the file itself while it's in flight.
- **Dispatch each leaf with `isolation: "worktree"`** on the `Agent` call. Each
  worker gets its own git worktree and branch — it is *physically* working on a
  separate checkout, so it cannot corrupt another in-flight leaf's uncommitted
  changes even if scopes were misjudged. You merge the branches back afterward,
  one at a time.
- **Dispatch every currently-READY leaf, not just the ones that feel like "the next
  step."** After each merge, recheck the whole tree for newly-unblocked leaves and
  add them to the next wave immediately (rolling dispatch) — don't wait for a whole
  wave to finish before starting the next one, and don't leave a READY leaf sitting
  idle because you're mentally still focused on a different branch of the tree.
- Fire every currently-READY leaf's `Agent` call in the **same message** (multiple
  tool-use blocks, one turn) so they actually run concurrently, and leave them in
  the background — don't block waiting on one before starting the next.

The worker's job is not just "implement this." It is "implement this, then prove it
— in detail, for your section specifically." Each worker owns thorough testing of
its own leaf: real edge cases and boundary conditions for what it built, not just a
single happy-path check, since it's the one worker with the context to know what
could actually go wrong in its own piece. The worker must actually execute its own
gates via Bash before reporting back, and report FAIL with a real diagnosis rather
than guess at PASS if it can't get a gate green. This is what keeps a hallucinated
"looks right to me" from ever reaching you as a false success. The exact prompt
template to hand each worker, and the merge procedure once it reports back, are in
`references/dispatch-protocol.md` — use that template rather than improvising one
per leaf; it's what encodes the self-test requirement, the owner-scope boundary, and
the interface-contract technique for widening a wave.

## 7. You re-verify — worker self-report is evidence, not proof

When a worker reports back (with the worktree path + branch name), do not mark the
leaf VERIFIED off its say-so alone:

1. Merge its branch into your integration branch (`git merge`). If the merge isn't
   clean, that itself is a finding — diagnose whether the owner scopes actually
   overlapped or the worker touched files outside its scope.
2. Re-run that leaf's own gate(s) yourself, against the merged tree. This is cheap
   (gates are supposed to be small) and it catches two different failure modes at
   once: a worker that misread its own output, and a merge that broke something the
   worker never saw.
3. Only on a clean merge + a gate you just watched pass do you set the task to
   `completed` with `metadata.state = "VERIFIED"`.

If the re-run fails even though the worker reported PASS, treat that as real
information about the worker's reliability on this leaf, not an annoyance — diagnose
it same as any other failure (see below) rather than silently re-running until it
happens to pass.

## 8. Integration gates: children green does not mean parent green

Components that are each individually correct can still be incompatible together —
mismatched field names, incompatible assumptions, a shared resource two leaves both
assumed they owned. That's exactly what independent parallel workers are prone to
producing, since neither one sees the other's code while working.

So a branch is not VERIFIED just because all its leaves are. Once every leaf under a
branch is merged and re-verified, run (or write, then run) an integration gate for
that branch — something that actually exercises the pieces together (an end-to-end
flow, a real request against the real merged API, whichever fits). Do the same at
the root once every branch is VERIFIED: root-level gates should exercise the system
as a whole. If an integration gate genuinely needs new test code rather than a
one-liner you can run directly, spin it up as its own leaf task (usually medium/hard
difficulty — integration bugs tend to be subtle) rather than writing it inline under
time pressure.

## Failure handling: diagnose before you fix

A failing gate is information, not a verdict on the product and not something to
route around. Before changing anything, figure out *which* of these it is: an
implementation defect, a bad gate (wrong EXPECT, testing the wrong thing), an
environment problem, a missing dependency, or an integration mismatch. Fix the thing
that's actually wrong, then re-run the gate — never edit a gate's EXPECT just to make
a red check turn green; that converts your one honest signal into a lie.

If a leaf fails repeatedly with no real change in outcome, that's a no-progress
loop — escalate the model tier, or if it's genuinely blocked (missing access, a
dependency that doesn't exist, a requirement that turns out to be impossible as
stated), mark it `metadata.state = "ABANDONED"` with `metadata.abandon_reason`
explaining why, and say so to the user. Abandoned is not verified — if the root
contract still needs that outcome, the root is still not done. Only the user
narrowing the contract makes an abandoned leaf stop counting.

## Before you say "done"

Run `TaskList` and check, for every task under the root that the current contract
still requires:

```
[ ] nothing is pending with no owner (nothing sitting READY, undispatched)
[ ] nothing is pending with open blockedBy (nothing stuck WAITING)
[ ] nothing is in_progress (nothing IN-FLIGHT)
[ ] every completed task has metadata.state == "VERIFIED" (not silently just "completed")
[ ] any ABANDONED task's requirement has been explicitly dropped from the contract by the user, or it's still open
[ ] branch integration gates have run and passed
[ ] root integration gates have run and passed
```

If any line fails, the task is not done — keep working, or give the user an honest
handoff: what's verified, what's unresolved, why, what you tried, and what finishing
it would need. "37 of 40 gates pass" is a useful progress report. It is not "done,"
and you should never present it as such.
