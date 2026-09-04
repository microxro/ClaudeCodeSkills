# Apple App Store — deployment & submission reference

> **Before treating any number here as current fact:** dates, SDK/OS version
> requirements, fees, and size limits drift over time and this file is a
> snapshot. Treat it as a strong starting checklist and the right shape of
> thing to check — not a substitute for confirming a decision-critical
> figure (a hard size limit, a submission deadline, a fee, an SDK
> requirement) against Apple's current official documentation before it
> drives a real decision. This is the anti-invention principle from
> `SKILL.md` applied to this file itself: a specific-sounding number is not
> automatically a verified one.

## Contents
- [Official policies & submission guidelines](#official-policies--submission-guidelines)
- [App listing & metadata](#app-listing--metadata-best-practices)
- [Technical build & performance](#technical-build--performance-recommendations)
- [Security, privacy & data handling](#security-privacy--data-handling-requirements)
- [Common rejections & mitigation](#common-review-rejections--mitigation)
- [CI/CD & deployment tips](#cicd--deployment-tips-ios)
- [Monitoring, analytics & crash reporting](#monitoring-analytics--crash-reporting)
- [Accessibility & UX guidelines](#accessibility--ux-guidelines)
- [Pre-submission checklist](#pre-submission-checklist)
- [Post-release checklist](#post-release-checklist)
- [Example metadata & release notes](#example-metadata--release-notes)
- [Key constraints comparison](#key-constraints-comparison)

**Executive summary:** Apple enforces strict guidelines to ensure quality,
privacy, and security. Your app's product page (name, subtitle, icon,
description, screenshots, etc.) must be polished and compliant. Use the
latest Xcode and iOS SDK, sign your app with valid certificates, and enable
App Transport Security (HTTPS). Prepare a complete Privacy Nutrition Label
(data practices) and optional Accessibility Label in App Store Connect. Test
thoroughly (using TestFlight) to avoid common rejection causes (crashes,
private APIs, missing metadata). Automate builds and submissions via Xcode
Cloud or Fastlane, and follow Apple's checklists before and after release.

## Official policies & submission guidelines

- **App Review Guidelines** — all apps are reviewed for content, privacy,
  security, and reliability. Undocumented APIs, inappropriate content, and
  misleading metadata are explicitly prohibited. Always test that the app
  works as advertised on supported devices.
- **App Store Connect requirements** — a completed App Privacy form
  (generates the Privacy Nutrition Label) and, where relevant, Accessibility
  support details (VoiceOver, captions, etc.) are mandatory for submission of
  new apps and updates.
- **Latest SDK/Xcode** — new apps must be built with a recent Xcode/iOS SDK;
  confirm the currently required version before submitting, this moves.
  Ensure the project's deployment target and code are compatible with recent
  OS versions.
- **Developer agreements** — maintain active Apple Developer Program
  membership; keep certificates, provisioning profiles, and App Store
  contracts current.

## App listing & metadata best practices

- **App name (title):** ≤30 characters, accurately describing the app's core
  function. Avoid generic/promotional terms ("Free", "Best") — a common
  rejection trigger.
- **Subtitle:** 30 characters, highlighting a key feature or appeal; appears
  below the app name.
- **Keywords:** 100 characters, comma-separated, no spaces/synonyms/repeated
  words. Order doesn't matter to Apple's search — prioritize high-traffic,
  app-specific terms and brand names.
- **App icon:** simple, recognizable, 1024×1024 px square (App Store Connect
  generates smaller sizes). Avoid text/logos illegible at small sizes.
- **Screenshots & previews:** high-quality per device family (iPhone, iPad,
  iMessage, Apple Watch, etc.) at the largest device's resolution (e.g.
  iPhone 6.7″ at 1284×2778 px, iPad Pro 12.9″ at 2048×2732 px) so App Store
  Connect can auto-scale. Show real UI, minimal decoration (no "Play"
  overlays), illustrate core features. Video previews (15–30s, 1080p+) can
  demonstrate key flows.
- **Promotional text & description:** description up to 4000 characters,
  leading with the main benefit, short bullet lists for readability. No
  "#1"/price-incentive marketing language. Use promotional text for
  notable, time-sensitive updates.
- **Localization:** localize title, description, and screenshots for every
  target language/region — meaningfully increases reach.
- **Additional fields:** subtitle, promotional text, in-app purchase list
  (if applicable), accurate content rating, privacy policy URL. Missing or
  inconsistent info delays approval.

## Technical build & performance recommendations

- **Packaging:** sign a properly archived `.ipa`; keep uncompressed app size
  under Apple's current limit. Use App Thinning and On-Demand Resources to
  cut user download size; be mindful of the cellular download size limit.
- **Code signing & provisioning:** sign with a valid Apple Distribution
  certificate and matching provisioning profile. Bundle ID, version, and
  build number must be unique and correct — mismatches cause rejection.
  Xcode Cloud or Fastlane can automate signing and upload.
- **Entitlements & capabilities:** enable only capabilities actually used
  (Push Notifications, iCloud, Background Modes, ...). Justify background
  modes in submission notes and set the correct `UIBackgroundModes` keys —
  declaring a capability you don't really use is a rejection trigger.
- **API usage:** public APIs only. Private/undocumented API calls cause
  immediate rejection. Comply with framework-specific rules (Apple Pay,
  HealthKit, etc.) when used.
- **Networking security:** App Transport Security requires HTTPS/TLS (1.2+)
  for all network requests. Any exception needs a justified
  `NSAppTransportSecurity` entry in `Info.plist`.
- **Performance:** minimize launch time, keep view hierarchies simple, use
  Instruments to find leaks. Frequent crashes or unresponsiveness are a
  rejection cause. Stable apps typically run well under normal memory
  budgets for their device class.
- **Testing:** real devices, XCTest/UI tests for regressions, TestFlight for
  external beta testing across devices before public release. Cover first
  launch, login/purchase, and core feature flows.

## Security, privacy & data handling requirements

- **Privacy Nutrition Label:** declare every data type the app or its SDKs
  collect/use in App Store Connect, including whether it's tracked or
  linked to a user. Keep it current as practices change — discrepancies can
  cause delisting or rejection.
- **User consent:** always show the system permission dialog before
  collecting sensitive data (location, contacts, camera, microphone, ...);
  supply clear `Info.plist` usage-description strings (e.g.
  `NSCameraUsageDescription`). Offer Sign in with Apple where other social
  logins are offered.
- **Data security:** encrypt sensitive data in transit (HTTPS/ATS) and at
  rest. Never store credentials insecurely; use Keychain or other
  OS-provided secure storage for local personal info.
- **Regulations:** comply with applicable law (GDPR, COPPA for kids' apps,
  CCPA, etc.); include a privacy policy URL when required.
- **Third-party SDKs:** audit every included library — you're responsible
  for reporting and for the actual behavior of what they collect. Remove or
  update SDKs that over-collect.

## Common review rejections & mitigation

- **Crashes/instability** → fix all crashes, test across OS versions,
  optimize memory.
- **Private APIs** → check your binary/link map for undocumented symbols
  before submitting.
- **Inaccurate metadata** → no repetitive keywords, false claims, or
  description content the app doesn't actually have.
- **Incomplete app information** → missing screenshots for a device family,
  a missing privacy policy when required, or gaps in the product page. Work
  through the App Store Connect checklist before submitting.
- **Content violations** → no pornographic/defamatory/excessively violent
  content; moderate user-generated content; age-appropriate handling and
  parental consent for kids' apps.
- **Accessibility non-compliance** → if accessibility support is declared
  (or reasonably expected), the UI needs to actually work with VoiceOver
  etc. Test with the Accessibility Inspector.
- **Permission abuse** → don't request a high-risk permission (e.g. location
  "always") the feature doesn't clearly need.

## CI/CD & deployment tips (iOS)

- **Automated builds:** Xcode Cloud, GitHub Actions, or Bitrise; Xcode Cloud
  integrates directly with App Store Connect/TestFlight. Fastlane is a
  common scripting alternative.
- **Build once, promote everywhere:** one archive promoted across
  TestFlight/staging/production, not rebuilt per stage — avoids
  inconsistency between what was tested and what ships.
- **Versioning:** increment the build number every CI build; keep
  `CFBundleShortVersionString`/`CFBundleVersion` consistent with a semantic
  scheme.
- **Automated testing:** unit/UI tests in the pipeline on every PR;
  snapshot or smoke UI tests for fast regression coverage.
- **Provisioning:** automate certificate/profile management (e.g. Fastlane
  Match) to avoid manual signing errors.
- **Rollouts:** phased release after approval (e.g. 10% → 50% → 100%) to
  limit blast radius.
- **Release notes:** write real, specific "What's New" copy — what changed,
  what was fixed, not filler.

## Monitoring, analytics & crash reporting

- **App Analytics** in App Store Connect for downloads/sales/usage/retention;
  add an SDK (Firebase, Mixpanel, ...) for in-app event tracking if needed.
- **Crash reporting** via Firebase Crashlytics, Sentry, or Xcode Organizer's
  device-collected crash logs. Track crash-free rate as a real metric, not
  a vibe.
- **Performance monitoring** via Instruments pre-release, and App Store
  Connect's post-release metrics (launch time, energy impact).
- **Review feedback:** address every point in a rejection specifically and
  use the Resolution Center to respond or escalate.

## Accessibility & UX guidelines

- **Perceivable:** support Dynamic Type; verify color contrast against
  WCAG guidance for the text size in question.
- **Operable:** interactive elements sized for real touch targets; VoiceOver
  labels/hints set on UI elements.
- **Understandable:** follow the Apple Human Interface Guidelines — familiar
  patterns, help text where genuinely needed.
- **Robust:** provide an Accessibility URL in App Store Connect describing
  what the app actually supports (don't claim more than is true — see
  "accessibility non-compliance" above).
- **Testing:** Accessibility Inspector, VoiceOver itself, not just a
  checklist read-through. Never rely on color alone to convey information.

## Pre-submission checklist

- [ ] Version/build number updated; bundle ID and entitlements verified
- [ ] Metadata complete: title, description, subtitle, keywords, support
      URL, marketing URL, privacy policy URL
- [ ] Screenshots/videos for every required device size
- [ ] Privacy and Accessibility sections filled in App Store Connect
- [ ] Signed with a valid certificate and provisioning profile
- [ ] Run on-device, all crashes/bugs fixed, no private API usage
- [ ] App size and asset optimization checked
- [ ] Release notes written
- [ ] TestFlight build tested with beta users, if applicable

## Post-release checklist

- [ ] Monitor crash rate, reviews, and key analytics
- [ ] Respond to user reviews and feedback promptly
- [ ] Schedule fixes for anything found post-release
- [ ] Localize updates and marketing assets for additional regions
- [ ] Plan future features/App Store In-App Events and promotional material

## Example metadata & release notes

- **App title:** "BudgetMate: Expense Tracker" (≤30 chars, no "Free"/brand
  puffery)
- **Subtitle:** "Track and manage your spending."
- **Keywords:** `budget,expenses,finance,tracking`
- **Description (excerpt):** "BudgetMate makes it easy to track your
  personal spending and savings. Automatically categorize transactions, set
  budgeting goals, and view clear charts of your expenses. New in v2.0:
  added dark mode and monthly reports!"
- **Release notes:** "In this update we improved account sync stability and
  added CSV export. Fixed bugs with transaction editing. Enjoy the new
  calendar view!"

## Key constraints comparison

| Platform | File size limit | Asset requirements | Review time | Developer fee | Supported platforms |
|---|---|---|---|---|---|
| Apple App Store | Uncompressed app size capped (check current limit); cellular download size capped on older iOS | Icon 1024×1024 px PNG; screenshots per device (e.g. 1284×2778 px for 6.7″ iPhone) | Typically hours to ~1–2 days | Annual developer program fee | iPhone, iPad, Mac, Apple Watch, Apple TV, Vision Pro |
| Google Play | AAB base module capped (check current limit); per-device download capped | Icon 512×512 px; feature graphic 1024×500 px; screenshots ≥1080×1920 px portrait | A few hours to days | One-time Play Console registration fee | Android phones, tablets, Wear OS, TV, Auto |
| Vercel | Source upload and function bundle size vary by plan tier | No store assets — standard responsive web assets | Immediate (deploys on push) | Free tier available; paid tiers scale with usage/team size | Web frameworks (Next.js, React, Svelte, Node.js, etc.) |

Pipeline shape: `Xcode Build → TestFlight Beta → App Review → App Store Release`
