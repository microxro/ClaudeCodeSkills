# Writing gates that actually prove something

A gate is CHECK (a command you run) + EXPECT (what the result must show). Its whole
job is to move a claim from "I believe this works" to "I just watched this work."
That's only true if the gate is well-built — a sloppy gate gives you the ceremony of
verification without the substance.

## Keep gates small and single-purpose

One gate, one observable outcome. Don't write:

```
CHECK: the whole website is complete, responsive, secure, fast, and production-ready
```

That's not executable and it's not diagnosable when it fails. Write instead:

```
G1: main page returns 200 and renders the nav
G2: invalid login is rejected with 401
G3: valid login sets a session cookie
G4: mobile layout doesn't overflow at 375px width
```

Small gates are easier to write, easier to hand to a worker, easier to re-run
individually, and when one fails you know exactly what's wrong instead of "something
in this giant check is wrong."

## The pass rule

```
PASS = (exit code == 0) AND (output matches EXPECT)
```

Both halves matter. A command that exits 0 but prints the wrong thing is not a pass.
A command that prints the right-looking string but exits nonzero is not a pass
either — don't let a worker (or yourself) grade on vibes from the output alone.

## Gate quality is your responsibility, not the mechanism's

Running CHECK and matching EXPECT is mechanical. Whether CHECK actually tests the
right thing is a judgment call you have to get right, and it's the most common way
this whole approach fails silently. Example:

> Requirement: "calculator supports all arithmetic"
> Gate: `2 + 2 == 4`

That gate can be green forever while subtraction, division, decimals, and negative
numbers are all broken. Green here means "the declared check passed," not "the
requirement is satisfied" — those are only the same thing if you built the check to
actually cover the requirement. When you write a gate, ask "if the real bug I'm
worried about existed, would this CHECK actually catch it?" If not, it's the wrong
gate, not just an incomplete one.

## False green vs. false red

**False green** — the gate passes but the thing is actually broken. Usual causes:
EXPECT too loose, CHECK testing a superficial signal instead of real behavior, the
requirement never got represented in any gate at all, or integration was never
tested even though the pieces were.

**False red** — the gate fails but the thing is actually fine. Usual causes: the gate
itself has a bug, EXPECT is wrong, a missing dependency or wrong working
directory/shell, a flaky external service, a timeout that's too tight.

Both are reasons to *diagnose*, not reasons to distrust the whole approach. When a
gate fails, the first question is always "is this a real defect or a bad check?" —
answer that before touching anything (see SKILL.md's failure-handling section). And
the corollary: **never edit EXPECT just to turn a red gate green.** That's not fixing
the check, it's disabling your only honest signal while keeping the appearance of
having one.

## Gates are executable content — treat them that way

A CHECK is a real command with real access to whatever the environment gives it —
files, network, credentials, whatever the shell can reach. If you or a worker is
about to write a gate that shells out to something unfamiliar (a downloaded script,
an unreviewed binary), read it first the same way you'd review any other code before
running it. This matters more once workers are writing their own gates in parallel,
unsupervised in the moment — a gate is not just a passive assertion, it's a program.

## Worker self-verification: what "prove it" means in practice

When you hand a leaf to a worker (see `dispatch-protocol.md`), it must actually
execute its gates via Bash and look at the real output before claiming a pass — not
reason about whether the code "should" pass. If a gate can't be run in the worker's
environment for some structural reason, the worker should say exactly that rather
than assume success. "I couldn't verify this" is honest and useful; a guessed PASS
is not — it just moves the false-green problem from the gate design into the
worker's report, which is harder for you to catch later.
