# Vercel — hosting & deployment reference

> **Before treating any number here as current fact:** plan limits, default
> runtimes, and retention windows change over time and this file is a
> snapshot. Treat it as a strong starting checklist and the right shape of
> thing to check — not a substitute for confirming a decision-critical
> figure against Vercel's current official documentation before it drives a
> real decision. Same anti-invention principle as `SKILL.md` applied to
> this reference file itself.

## Contents
- [Official docs & guidelines](#official-documentation--guidelines)
- [Hosting & deployment workflow](#hosting--deployment-workflow)
- [Security, privacy & data handling](#security-privacy--data-handling)
- [Common pitfalls & mitigation](#common-deployment-pitfalls--mitigation)
- [CI/CD & deployment tips](#cicd--deployment-tips-vercel)
- [Monitoring, analytics & crash reporting](#monitoring-analytics--crash-reporting)
- [Accessibility & UX guidelines](#accessibility--ux-guidelines)
- [Pre-deployment checklist](#pre-deployment-checklist)
- [Post-deployment checklist](#post-deployment-checklist)
- [Example configuration & notes](#example-configuration--notes)

**Executive summary:** Vercel deploys web apps (static sites, Next.js/React,
etc.) to a global CDN plus serverless/edge functions, with every push
optionally triggering an automated deployment. Optimize bundle sizes,
leverage framework features like Incremental Static Regeneration (ISR) and
streaming, and use caching headers to exploit the framework-aware CDN.
HTTPS is on by default. Connect a Git repo so every PR gets its own Preview
deployment. Monitor with Vercel Analytics or a third-party tool. Treat
accessibility (semantic HTML, alt text, keyboard nav) as a real requirement
— it's a public website.

## Official documentation & guidelines

- The Vercel docs cover deployment (`vercel deploy`), Functions, Edge
  Functions, and Analytics — check them directly rather than assuming a
  behavior.
- Vercel optimizes out-of-the-box for common frontend frameworks (Next.js,
  React, Svelte, Vue, etc.) — confirm the framework in use is officially
  supported and check for framework-specific guidance.
- Review Vercel's Limits documentation for the active plan tier (Hobby vs.
  Pro vs. Enterprise) before assuming a number — limits differ meaningfully
  by tier.

## Hosting & deployment workflow

- **Git-driven deployments:** connect GitHub/GitLab/Bitbucket. A push to the
  production branch triggers a Production Deployment; other branches get
  Preview Deployments for QA. Vercel runs the framework's own build command
  automatically.
- **Environments:** use Vercel Environment Variables, scoped separately for
  development/preview/production, for API keys and secrets — never
  hardcode them.
- **DNS & domains:** custom domains via the dashboard; SSL/TLS is
  auto-provisioned. Allow time for DNS propagation before troubleshooting a
  cert issue as something else.
- **Edge network & caching:** static assets and ISR pages are served from
  the edge without an origin fetch on repeat visits by default. Dynamic
  pages/API routes need explicit `Cache-Control` or the framework's
  revalidation APIs to get the same benefit.
- **Static caching:** serve genuinely static content as static (e.g.
  `getStaticProps` in Next.js) to maximize cache hit rate.
- **ISR:** update page content in the background without a full redeploy —
  pages can serve stale-while-revalidating instead of forcing a rebuild for
  every content change.
- **Build optimization:** tree-shake, use a bundle analyzer, trim unused
  code; watch for framework-specific large-page warnings in the build
  output.
- **Build cache:** Turborepo (Vercel-supported) or `vercel.json` cache
  config for monorepos/repeated builds.

## Security, privacy & data handling

- **HTTPS by default:** every deployment is served over HTTPS; HTTP
  requests redirect. Modern TLS is used automatically.
- **SSL certificates:** auto-provisioned per domain at no extra cost; a
  bring-your-own-certificate option exists if needed.
- **Data storage & functions:** don't store sensitive data directly on
  Vercel — use environment variables for secrets and an external managed
  database (e.g. a hosted Postgres/Mongo/Supabase) over a secure
  connection.
- **Privacy/legal:** if collecting user data via forms etc., comply with
  applicable privacy law and publish a real privacy policy.
- **Bot protection/firewall:** higher plan tiers offer an edge firewall for
  malicious-traffic filtering — check whether the current tier includes it
  before assuming it's active.
- **Function payload limits:** serverless functions have a default max
  response payload; for large uploads/downloads use external storage or
  streaming instead of pushing through the function response directly.

## Common deployment pitfalls & mitigation

- **Build failures** — often a missing environment variable or an
  unexpected Node version; check the build logs first, and pin the Node
  version explicitly (`engines` in `package.json`) if the default doesn't
  match what's needed.
- **Exceeding limits** — a large function bundle or source upload can hit a
  plan's size cap; trim dependencies, or move to a tier with headroom.
- **Routing issues** — a misconfigured `vercel.json` rewrite/redirect is a
  common source of broken routes; review it directly rather than guessing.
- **Caching problems** — stale content from an overly aggressive
  `Cache-Control`; use `no-cache` on APIs/webhooks that must always be
  fresh, and test headers locally (`vercel dev`) before trusting them in
  production.
- **SSL certificate errors** — usually a DNS CNAME not actually pointing at
  Vercel; follow the custom-domain setup exactly rather than assuming it's
  a Vercel-side issue.
- **Domain limits** — lower tiers cap domains per project; check the
  current cap before assuming headroom.

## CI/CD & deployment tips (Vercel)

- **Preview deployments:** every PR gets a shareable preview URL — use it
  for real QA and stakeholder sign-off, not just a formality.
- **Protected merges:** gate the production branch on passing checks so
  only a validated build reaches production.
- **Instant rollback:** revert to a previous deployment instantly if an
  issue surfaces post-deploy — no need to redeploy an old commit.
- **Edge Functions:** for low-latency logic on frameworks that support
  them; check current invocation-time limits before relying on a
  long-running edge function.
- **Build plugins:** community plugins (Sentry, image optimization, SEO,
  PostCSS, ...) can automate common build-time tasks.
- **Monorepos:** Turborepo for shared build caching, or set an explicit
  project root to target a subfolder.
- **Skew protection:** for frameworks that support it (Next.js/SvelteKit),
  to keep already-loaded clients compatible with assets during a rolling
  update.

## Monitoring, analytics & crash reporting

- **Vercel Analytics:** built-in real-user metrics (Web Vitals, pageviews)
  without extra client JS — useful first stop for performance insight.
- **External analytics:** Google Analytics, Plausible, etc. via script/SDK
  as needed.
- **Logging:** dashboard logs have a retention window that's typically
  short — pipe to an external logging service (Logflare, Papertrail, etc.)
  for anything needing longer retention.
- **Uptime monitoring:** an external check (e.g. UptimeRobot) on the live
  URL, even though Vercel's own uptime is generally strong — don't treat
  platform reliability as a substitute for your own alerting.
- **Error reporting:** wrap serverless function handlers to report runtime
  errors to Sentry or similar rather than relying on log-reading alone.

## Accessibility & UX guidelines

- **Semantic HTML:** real headings, landmarks (`<nav>`, `<main>`), labeled
  form fields — screen readers depend on correct semantics, not just
  visual layout.
- **Keyboard navigation:** every interactive element reachable and usable
  via Tab/Shift+Tab; actually test this, don't assume it from using
  standard elements.
- **Images:** `alt` text on every meaningful image; empty `alt=""` for
  purely decorative ones.
- **Color contrast:** WCAG-guided contrast ratios (commonly cited: 4.5:1
  for normal body text) — check with a real tool (axe, Lighthouse), don't
  eyeball it.
- **Responsive design:** layouts that genuinely work across mobile and
  desktop, not just at one reference width.
- **UX:** lazy-load images/heavy assets, clear loading states and form
  error messages.

## Pre-deployment checklist

- [ ] Local build passes (`npm run build` / `vercel build`)
- [ ] Production environment variables set correctly, no secrets in logs
- [ ] Accessibility audit run (Lighthouse/axe), critical issues addressed
- [ ] Performance audit run (Speed Insights/Lighthouse), large
      scripts/images addressed
- [ ] Dependency security check (e.g. `npm audit`) run, deps current
- [ ] No test/debug content left in; static-generation fallback/revalidate
      logic correct where used
- [ ] Serverless function sizes checked against plan limits
- [ ] `Cache-Control` set appropriately for static assets

## Post-deployment checklist

- [ ] Deployment status confirmed, preview URLs verified working
- [ ] Analytics (built-in or external) confirmed recording real traffic
- [ ] Custom domain loads over HTTPS with no certificate warnings
- [ ] Logs checked for unexpected 5xx errors, fixed and redeployed if found
- [ ] Scaling/caching reviewed if expecting a real load spike
- [ ] Slow initial load or build times revisited (code-splitting, ISR)

## Example configuration & notes

`vercel.json` rewrite example:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://api.example.com/:path*" }
  ]
}
```

Release notes example (`CHANGELOG.md` or GitHub Releases):

> **v1.2.0 (2026-08-20):** Added real-time chat with Socket.io. Improved
> image loading speed with WebP fallback. Fixed IE11 styles. UI tweaks and
> bug fixes.

Pipeline shape: `Push → Build → Preview/Production Deploy → (optional) Rollback`
