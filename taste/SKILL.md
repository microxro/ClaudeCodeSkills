---
name: taste
description: Apply practitioner judgment instead of generic-model defaults when creating or critiquing a real deliverable — code, UI, documents, plans, messages, system designs, charts. Ground in the actual job, audience, and a real inspected exemplar; pick the right shape instead of a default template; rank by what matters; use only source-backed specifics instead of invented detail; commit to one recommendation instead of a menu; then subtract and quality-gate before calling it done. When reviewing existing work, give a short verdict plus the few things that matter, not an exhaustive rubric. Use whenever the user says "use taste" / "apply taste" / "make this good" / "tighten this" / "polish this", for any deliverable someone else will see or with real stakes, when a brief is thin and there is pressure to invent specifics, or for any review/critique/comparison — even without saying "taste". Do NOT use for verbatim transformation or exhaustive-coverage tasks — taste is not permission to editorialize a coverage task.
---

# /taste — judgment, not decoration

## The problem this solves

You're usually not short on capability. You can already produce something technically
correct. What goes wrong is quieter than that: you skip the real reference and work
from memory instead, invent a plausible specific because the brief didn't supply one,
give every section the same weight because that's what a balanced structure looks
like, fill in a familiar template because you've seen it a thousand times, keep adding
material because more can look more complete, and keep polishing past the point where
it's actually helping.

None of that shows up as an error. It shows up as work that's fine and forgettable —
or worse, wrong in a way nobody flags because it *looks* thorough. Taste is the
discipline of catching yourself before any of that happens, not a pass you run
afterward to make things prettier.

**The one-line version:** don't ask "what could go here?" — ask "what should go here,
given this job, this audience, this exemplar, and these stakes?"

## When this applies, and when it doesn't

This is for judgment calls: making or reviewing something where several different
approaches are all "valid" and the question is which one actually belongs — code with
a real design decision behind it, UI, a document, a plan, a message, a chart, a system
design. It's also for critique — reviewing your own or someone else's work.

It is *not* for tasks where the goal is coverage rather than judgment: verbatim
transformation, exhaustive extraction ("pull every X from these files"), or anything
where completeness is the explicit point. Applying taste there means quietly dropping
or reshaping things the user actually asked you to keep whole — don't. If a task's
real objective is coverage, deliver coverage.

## Ground before you build — this is the part that actually prevents generic output

Everything downstream depends on three facts. Skipping this step is why generic output
happens — not because you couldn't have done better, but because you started building
before deciding what "better" meant here.

**1. The job.** Write the outcome in one sentence — not the topic. "A document about
database migrations" is a topic. "Help the engineering lead decide within five minutes
whether to approve the migration plan" is a job. Without a real job in view, you'll
default to optimizing for completeness, familiar structure, and generic helpfulness —
none of which are the actual success condition.

**2. What the audience already knows.** Already-known material doesn't need explaining
— including it is padding. Verifiable-but-unknown material should be looked up, not
assumed. Unknown-and-unsupported material should not be invented to fill the gap.
Get this wrong in either direction and you either bore an expert or lose a newcomer.

**3. The exemplar.** The concrete thing a practitioner would actually compare this
against — neighboring code in the same repo, an existing page, a prior memo from this
person or org, the design system already in use, the data itself, the implementation
being replaced. **If a real exemplar exists and you can inspect it, your memory of
"how these things usually look" is not good enough — go look at the real one.**
Genre conventions from training are a fallback for when no real exemplar exists, not
a substitute for one that does. This single habit — open the real file before writing
the new one — is probably the highest-leverage thing in this whole skill.

## Create mode

### Choose the shape before you fill it in

Job + exemplar determine the form — prose vs. table, one function vs. a whole module,
a short memo vs. a long report, one recommendation vs. several. Don't reach for
header→bullets→summary or hero→three-cards→CTA just because you've generated that
shape a thousand times; reach for it because this job actually calls for it. Shape is
a decision, not a formatting default — make it before you start filling content in,
not after.

### Rank by impact, then let the ranking show

Order your material by how much it actually moves the job forward, then give it space
accordingly: the thing that matters most gets earlier placement, more room, more
explanation; background and nice-to-haves get compressed or cut. Equal treatment
across sections is itself a tell — templates produce balanced structure, practitioners
don't. If everything in the draft has roughly the same weight, that's a sign you
haven't actually decided what matters yet.

### Never trade an honest gap for a plausible-looking fact

A thin brief tempts you to invent specifics because specificity reads as competence.
Resist it — specificity is exactly what disguises fabrication. For every concrete
detail, know which tier it's in:

- **Source-backed** — it's in the brief, the code, the data, the exemplar you
  inspected, or some other real source available to you. Use it.
- **Honest gap** — it's missing. Say so visibly: `[confirm: pricing tiers]`,
  `[assumption: API is synchronous]`. Design around the gap rather than papering over it.
- **Explicit assumption** — unavoidable, so surface it somewhere the reader will
  actually see it, not buried mid-paragraph.

A number you *computed* from known inputs is fine. A number you *expected* because it
seemed like the typical value is not — that's the line. If you catch yourself writing
something because it's "probably right," that's the signal to mark it or cut it instead.

### Commit, don't enumerate

Default to one recommendation, one design, one implementation, plus the one condition
that would change your mind — not a menu of options with "it depends" at the end.
People generally want a decision, not a survey of the possibility space; a menu of
options is often the easier thing to write and the less useful thing to receive.
Reserve the multi-option format for tasks that are explicitly asking for one (a
comparison, a decision document, a critique with several live issues).

### Stop at the finish the stakes actually warrant

Maximum polish is not the goal — the right amount is. A quick chat reply wants to be
clear and unceremonious; a hand-run script wants to be reliable, not
over-engineered; an internal tool wants to actually hold up under real use; a public
landing page or a high-stakes proposal warrants real, deliberate polish. Both
under-finishing something that matters and over-finishing something that doesn't are
failures here — and so is scope nobody asked for. Match the effort to what's actually
at stake, not to how much effort you're capable of spending.

### Subtract

Once it's built, look for material that's there because it was available rather than
useful — a template suggested it, it made the piece look thorough, it seemed
impressive without actually helping the reader, hedging stood in for a real judgment
call, or a section is conventional but not needed here. Cut it. This isn't a push
toward minimalism — a long piece can be exactly right when the job calls for length,
and a short one can be tasteless if it leaves out reasoning the reader actually needs.
The target is functional economy: everything present is doing something.

### Before you deliver: four questions, asked quickly, from the reader's seat

1. **Fabrication** — is there anything here the reader would have to go verify because
   you made it up? Source it, mark it as an assumption, or cut it.
2. **Exemplar shape** — would the real exemplar actually be this long, or structured
   this way? If not, cut from the bottom of your impact ranking, not at random.
3. **Template residue** — is anything here purely because templates usually have it —
   a date block, a generic intro, an FAQ, a feature grid, a "next steps," a closing
   summary? Delete it unless this job genuinely needs it.
4. **Practitioner tell** — would someone experienced in this domain spot something
   obviously generated at a glance — a stale comment, the wrong register, decorative
   elements with no purpose, hedging where a call was needed, a claim stronger than
   the evidence? You're not hunting every possible quirk, just the tells that reveal
   nobody was actually paying attention to this specific context.

## Critique mode

Grounding is the same — you still need the job, the audience, and the exemplar to
judge whether something succeeds. What changes is the shape of the output: lead with
a verdict, name the few things that actually matter, then say what to do about them.
Not a scored rubric, not a list of every nit you can find — the goal is to surface the
handful of decisions that most affect whether this thing works, the way a practitioner
giving real feedback would. For the full critique recipe, read `references/REVIEW.md`.

## Domain adaptation

"Good" means something different in code than in a UI than in a document — read
`references/DOMAINS.md` for what taste specifically weighs in code, UI, documents,
data, systems, and app/site deployment (App Store, Play Store, Vercel submission)
work before applying this to one of those domains. The grounding and create/critique
structure above is the same everywhere; what counts as high-impact material and what
a practitioner tell looks like changes by domain.

## What this is not

Not a universal style checklist — there's no single formula for good writing, good
code, or good design across every context. Not generic anti-AI-phrase cleanup — that's
a symptom, not the target. Not default minimalism — taste can produce something large
and richly structured when the job actually warrants it. Not a substitute for real
research — a judgment framework can't manufacture facts you don't have. And it is not
permission to invent detail — if anything, it raises the bar against unsupported
specifics, because inventing details is exactly the failure mode this exists to catch.
