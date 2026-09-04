# Domain adaptation

The grounding procedure and the create/critique structure in SKILL.md are the same
everywhere. What changes by domain is what counts as the exemplar, what "high-impact"
means, and what a practitioner would spot in five seconds. Read the section for
whatever you're actually making; skip the rest.

## Code

**Exemplar:** the neighboring code in this repo — not "how you'd typically write
this," but how this specific codebase actually does the equivalent thing elsewhere.
Open a few real files before writing new ones.

**What a tasteful decision prioritizes:**
- Fitting the abstractions that already exist here, rather than introducing a new
  pattern for something one existing pattern already handles.
- The smallest abstraction that clearly solves the actual problem — not the one that
  anticipates problems nobody has yet. "Add caching to this service" does not
  automatically mean a cache interface, Redis, invalidation abstractions, and a new
  directory hierarchy; it might mean twenty lines using the memoization helper the
  service already has. The amount of code should match the actual decision, not
  demonstrate thoroughness.
- Preserving local style — naming, error handling, structure — over what you'd
  personally default to.
- Minimizing new API surface. Every new public function/class/config knob is a thing
  someone else now has to understand and maintain.

**Practitioner tells:** speculative architecture for requirements that don't exist
yet, a new dependency for something a few lines would solve, config options nobody
asked for, comments that explain what the code does instead of why, tests that assert
implementation details rather than behavior.

## UI

**Exemplar:** the actual product — its existing components, spacing, interaction
patterns — not a generic design-system aesthetic or "what SaaS landing pages usually
look like."

**What a tasteful decision prioritizes:**
- Hierarchy that reflects what the user actually needs to notice first, not visual
  variety for its own sake.
- Interaction intent — does this control's affordance match what it actually does.
- Spacing and rhythm consistent with the rest of the product, not a fresh set of
  values because this screen felt like it needed its own system.
- Restraint on decorative elements. A gradient hero, a stats strip, or a testimonial
  carousel earns its place by serving this specific screen's job — not because
  templates in this genre usually have one.

**Practitioner tells:** a component that doesn't match anything else in the product,
decoration with no functional purpose, copy that reads like placeholder ("Lorem
Ipsum"-adjacent phrasing, generic feature-grid text), inconsistent spacing that
suggests nobody looked at the surrounding screens.

If the UI work in question is a store listing (App Store/Play Store screenshots,
icon, description) or a site about to go live, see "App & site deployment" below
too — those platforms have their own concrete, checkable requirements on top of
general UI judgment.

## Documents (memos, proposals, reports, messages)

**Exemplar:** a previous real document of this type from this person or
organization — its length, its structure, where it puts the decision, its register.

**What a tasteful decision prioritizes:**
- Reader decision time — how fast can the actual reader get to what they need,
  not how complete the document looks.
- Information hierarchy that puts the load-bearing content first, background last
  (or cut).
- Evidence placed next to the claim it supports, not collected in an appendix nobody
  reads.
- Matching this organization's actual communication norms over generic
  business-document convention.

**Practitioner tells:** an executive summary that just restates the title, a
background section longer than the actual point, a FAQ or "next steps" section that
exists because documents like this usually have one, hedged language where the
document should just state the recommendation.

## Data (analysis, charts, dashboards)

**Exemplar:** the underlying data itself, and how this organization has presented
similar findings before.

**What a tasteful decision prioritizes:**
- The chart/table form that actually fits the comparison being made — not whichever
  is most visually interesting. A single trend often wants a line, a few categories
  often want a bar, a precise lookup often wants a table; don't reach for a fancier
  visualization because it's available.
- Showing the number that answers the actual question, not every number that could
  be computed from the data.
- Labeling and axes that make the finding legible without the reader doing math in
  their head.

**Practitioner tells:** a dashboard with a dozen stat tiles and no clear "so what,"
a chart type chosen for visual novelty over legibility, precision implied that the
underlying data doesn't actually support (four decimal places on a rough estimate).

## Systems (architecture, technical design)

**Exemplar:** the current implementation being replaced or extended, and how this
organization has made comparable decisions before.

**What a tasteful decision prioritizes:**
- Solving the problem that's actually present, not the problem at ten times the
  current scale unless that scale is genuinely near.
- Operational reality — who runs this, how it fails, how it gets debugged at 2am —
  over architectural elegance.
- One clear recommendation with the condition that would reverse it, rather than a
  menu of architectures with tradeoffs listed for each (that's a decision document's
  job when explicitly asked for, not the default).

**Practitioner tells:** a design that introduces a new piece of infrastructure for a
problem the existing stack already handles, scale numbers with no basis, a proposal
that reads as technology-first ("let's use X") rather than problem-first.

## App & site deployment (App Store / Play Store / Vercel submission)

**Exemplar:** the platform's own current requirements — not memory of how
submission worked last time, since exact SDK versions, size limits, fees, and
policy details drift. This is one of the clearest cases where the anti-invention
rule in SKILL.md matters: a plausible-sounding version number or size limit is
worth exactly nothing if it's stale.

Detailed reference checklists for three platforms live alongside this file —
read whichever applies before doing real submission/deployment work, don't
reconstruct these from memory:
- `references/deploy-apple-appstore.md` — App Store metadata, review
  guidelines, entitlements, privacy nutrition label, common rejections
- `references/deploy-google-play.md` — Play Store listing, Data Safety form,
  Android Vitals, common rejections
- `references/deploy-vercel.md` — Git-driven deploys, caching/ISR, environment
  variables, common pitfalls

Every one of them opens with the same caveat worth repeating here: the specific
numbers in those files (SDK/API version requirements, size limits, fees,
percentages, effective dates) are a snapshot, not a live source. Treat them as
the right *shape* of thing to check — the categories that matter, the checklist
structure — and verify anything decision-critical (a hard limit a build will
actually hit, a submission deadline, a fee) against the platform's current
official docs before it drives a real decision, rather than presenting a
remembered number as current fact.

**What a tasteful decision prioritizes:**
- Getting the boring, checklist-shaped stuff right (metadata completeness,
  privacy disclosures, signing, size limits) before polishing anything visual —
  a rejection for a missing privacy answer wastes more time than any amount of
  icon refinement.
- Matching store-listing copy (name, subtitle, description, screenshots) to
  what the app actually does — the same anti-invention discipline as any other
  document: don't pad a listing with claims or a "download now!" urgency the
  product doesn't back up.
- Requesting only the permissions/entitlements/capabilities the app actually
  uses. An unused capability isn't neutral — it's both a rejection risk and a
  signal to a reviewer (or a later engineer) that nobody was paying close
  attention.
- A real device/beta test pass (TestFlight, an Internal track build, a Preview
  deployment) before submission, not just a local build that compiles.

**Practitioner tells:** screenshots that are decorative renders instead of the
real UI, a description padded with superlatives instead of specifics, a
requested permission with no corresponding feature, release notes that just say
"bug fixes and improvements," or a submission attempted against a remembered
SDK/size requirement nobody actually re-checked.
