# Google Play Store — deployment & submission reference

> **Before treating any number here as current fact:** dates, API level
> requirements, thresholds, fees, and size limits drift over time and this
> file is a snapshot. Treat it as a strong starting checklist and the right
> shape of thing to check — not a substitute for confirming a
> decision-critical figure against Google's current official documentation
> before it drives a real decision. Same anti-invention principle as
> `SKILL.md` applied to this reference file itself.

## Contents
- [Official policies & submission guidelines](#official-policies--submission-guidelines)
- [App listing & metadata](#app-listing--metadata-best-practices)
- [Technical build & performance](#technical-build--performance-recommendations)
- [Security, privacy & data handling](#security-privacy--data-handling-requirements)
- [Common rejections & mitigation](#common-review-rejections--mitigation)
- [CI/CD & deployment tips](#cicd--deployment-tips-android)
- [Monitoring, analytics & crash reporting](#monitoring-analytics--crash-reporting)
- [Accessibility & UX guidelines](#accessibility--ux-guidelines)
- [Pre-submission checklist](#pre-submission-checklist)
- [Post-release checklist](#post-release-checklist)
- [Example metadata & release notes](#example-metadata--release-notes)

**Executive summary:** Google Play is a flexible, data-driven platform for
Android apps and games. Follow the Play Developer Policies on content and
data use, and complete every required store listing field. Use a concise
app title (≤30 chars) and short description (≤80 chars), and design
marketing graphics (icon, feature graphic) per spec. Distribute as an
Android App Bundle (AAB), optimize code/resources with R8, and watch
Android Vitals for crashes/ANRs/memory. Declare privacy practices via the
Data Safety form. Use Play Console's testing tracks for staged releases,
monitor with Android Vitals/Firebase, and keep localized metadata and
release notes current.

## Official policies & submission guidelines

- **Developer Policy Center** — covers prohibited content, copyright,
  privacy, and ads. Violations (malware, impersonation, etc.) lead to
  rejection or removal; review the Content Policy and Store Listing &
  Promotion policy directly.
- **App Bundle requirement** — new apps are distributed as Android App
  Bundles (AABs), letting Play generate optimized per-device APKs. Enroll in
  Play App Signing to manage the signing key.
- **Data Safety & permissions** — complete the Data Safety form before
  publishing: what's collected/shared, why, and how it's secured. Sensitive
  permissions (location, SMS, contacts, ...) need justification in the form
  and listing. A privacy policy URL is required when personal/sensitive
  data is collected.
- **Target API level** — target a current Android API level for the modern
  permissions model; confirm the currently required minimum before
  submitting, this moves over time.
- **Testing tracks** — Internal/Closed/Open tracks to stage a release; push
  to Internal first for smoke testing, and use the Pre-Launch Report for
  automated device coverage.

## App listing & metadata best practices

- **App title:** ≤30 characters, the actual brand/app name — no keyword
  stuffing (Google penalizes repetition).
- **Short description:** ≤80 characters, front-loading the unique selling
  point; shows in search results.
- **Long description:** ≤4000 characters, short paragraphs/bullets, no
  ALL-CAPS or spammy CTAs ("Download now!"). First 2–3 lines should state
  the app's purpose plainly.
- **Icon & graphics:** icon 512×512 px PNG (32-bit), under Google's current
  size cap; feature graphic 1024×500 px illustrating the app's theme (no
  text-banner treatment); optional YouTube promo video. Avoid graphics that
  read as literal UI screenshots where a real screenshot slot exists
  instead.
- **Screenshots:** ≥2 per supported device form factor (phone, tablet,
  Android TV, Wear OS as applicable), preferred 1080×1920 px portrait or
  1920×1080 px landscape, showing real key flows. Localize screenshots
  alongside text where feasible.
- **Localization:** translate title, description, and graphical assets per
  target locale — localized listings meaningfully increase installs.
- **Promo text & release notes:** short promo text (≤170 chars) for
  time-sensitive announcements; concise, versioned "What's New" notes per
  release (what changed, not filler).

## Technical build & performance recommendations

- **Code optimization:** enable R8/ProGuard for shrinking, optimization, and
  obfuscation — reduces APK size, improves load time and RAM use; Play may
  set a minimum optimization bar for non-trivial apps (confirm current
  requirement).
- **App Bundle & asset delivery:** use Play Feature Delivery / Play Asset
  Delivery for large apps; keep the base module within Play's current
  compressed-size cap. Legacy OBB expansion files aren't used with AABs.
- **Memory usage:** stay within Android Vitals' foreground-memory
  thresholds for the device's RAM class; manage background tasks
  aggressively (don't hold large bitmaps while backgrounded); profile on
  low-end devices/emulators.
- **Background execution:** foreground services or JobScheduler for
  long-running work; background location on modern Android needs explicit
  approval and justification.
- **APK signing:** Play App Signing is required — upload an AAB and either
  supply your own key or let Google generate one; keep the keystore secure.
- **Multi-ABI support:** AABs auto-serve the right native libraries per
  device ABI instead of shipping a fat APK.
- **Versioning:** unique, increasing `versionCode` per release; user-facing
  `versionName`.
- **Build tools:** recent Android Gradle Plugin/Gradle; offline mode in CI
  for speed; strip debug logging/lint noise from production builds.

## Security, privacy & data handling requirements

- **Data Safety section:** accurately declare every data type collected and
  whether it's shared/encrypted — shown directly to users on the listing.
  A mismatch between declared and actual practice is a policy violation,
  not just a metadata nit.
- **Privacy policy:** required URL, in the listing and in-app, when
  personal/sensitive data is collected — explain collection, use, and user
  rights.
- **Secure transmission:** HTTPS/TLS for all server communication; modern
  Android blocks cleartext by default — any `networkSecurityConfig`
  exception should be minimal and justified.
- **Runtime permissions:** request dangerous permissions only when actually
  needed, with a clear rationale shown to the user.
- **Restricted permissions:** SMS, Call Log, Usage Stats, body sensors, etc.
  need explicit declaration/justification per Google's restricted
  permissions policy.
- **User-generated content:** moderation and reporting/blocking mechanisms
  if the app allows community content.
- **Encryption & keys:** certificate pinning where warranted for sensitive
  data; never hardcode API keys/secrets in the client.

## Common review rejections & mitigation

- **Policy violations** — spam/malware, inappropriate content, unauthorized
  data harvesting, impersonation. Review the Developer Policy Center
  directly rather than assuming.
- **Spammy listing** — repetitive/irrelevant title or description content,
  competitor names, keyword stuffing.
- **Technical crashes** — poor Android Vitals (crash/ANR rate) can trigger
  warnings or removal; test under real load before release, Firebase Test
  Lab or similar for device coverage.
- **Device compatibility** — an over- or under-restrictive `<uses-feature>`/
  `<compatible-screens>` filter can misfire; verify it matches the app's
  actual requirements.
- **Privacy & permissions** — incomplete/misleading Data Safety answers, or
  a sensitive permission requested without a clear in-app benefit.
- **Security flaws** — known vulnerabilities (e.g. outdated WebView)
  flagged; keep dependencies current.
- **App integrity** — Play scans for tampering/repackaging; only upload
  original signed AABs.

## CI/CD & deployment tips (Android)

- **Automated deployment:** Google Play Developer API, Fastlane `supply`, or
  `gradle-play-publisher` for scripted, consistent uploads and track
  management.
- **Build once, release everywhere:** the same signed AAB promoted across
  tracks, not rebuilt per stage.
- **Pre-launch testing:** an Internal track build per commit so QA can pull
  it directly; enable Play's pre-launch automated device reports.
- **Version codes:** an automated scheme (timestamp or semantic) to avoid
  collisions; keep `versionName` human-friendly for the listing.
- **Phased rollout:** release to a percentage of users first (e.g. 10% →
  50% → 100%) before full rollout.
- **Changelogs & promotion:** real release notes; Play Store Listing
  Experiments for A/B testing descriptions/graphics where available.
- **Backups & keys:** back up the original signing key and keystore/API
  credentials securely — Play App Signing doesn't remove the need for this.

## Monitoring, analytics & crash reporting

- **Android Vitals** in Play Console for crash rate, ANR rate, wake locks,
  and other core health metrics — track against Google's bad-behavior
  thresholds, don't just glance at them.
- **Firebase Crashlytics** for real-time crash reports with stack traces;
  Firebase Performance Monitoring for slow-operation tracing.
- **Analytics** (Firebase Analytics or similar) for DAU, conversion, and
  funnel drop-off.
- **User feedback:** monitor Play Store reviews and the Play Console
  feedback/crash-cluster views.
- **Error reporting:** in-app logging (e.g. Sentry) for non-crash logic
  errors.
- **Automated alerts** for spikes in crashes or policy-relevant behavior.

## Accessibility & UX guidelines

- **Contrast:** ≥4.5:1 for normal text, ≥3:1 for large text, per WCAG
  guidance; scalable `sp`/`dp` units.
- **Touch targets:** minimum 48×48 dp; Material components default to this,
  custom views need checking.
- **Content descriptions:** `contentDescription` on every non-text
  interactive element for TalkBack; explicitly hide purely decorative
  elements from the accessibility tree.
- **D-pad/keyboard navigation:** verified directly if targeting Android
  TV/Auto.
- **Testing:** Accessibility Scanner, actual TalkBack use — not just a
  visual read-through.
- **UX design:** Material Design conventions, simple and error-tolerant
  flows, clear form error messages with an easy correction path.

## Pre-submission checklist

- [ ] `versionCode`/`versionName` updated, AAB rebuilt and signed
- [ ] Clean release build run through CI/local pipeline
- [ ] Data Safety form completed in Play Console
- [ ] Store listing metadata complete and localized: title, descriptions,
      icon, feature graphic, screenshots
- [ ] Screenshots per device type, graphics meet current spec
- [ ] Privacy policy URL valid, if required
- [ ] Tested across a real spread of Android versions/devices, no
      crashes/ANRs
- [ ] Sensitive permissions audited — unused ones removed, each remaining
      one justified
- [ ] Lint/security warnings addressed
- [ ] Release notes and marketing copy prepared

## Post-release checklist

- [ ] Monitor Android Vitals and Crashlytics
- [ ] Check reviews for recurring complaints (performance, UX)
- [ ] Ship hotfixes promptly via staged rollout if needed
- [ ] Review analytics (demographics, retention, conversion) and adjust
- [ ] Consider store-listing A/B tests if install rate is low
- [ ] Keep the app current against new OS versions and libraries

## Example metadata & release notes

- **App title:** "PhotoShare – Photos & Videos" (≤30 chars)
- **Short description:** "Instantly share moments with friends." (≤80
  chars)
- **Long description (excerpt):** "PhotoShare lets you upload and browse
  photos in seconds. Customize your profile, create albums, and chat with
  friends directly in the app. New in v5.0: AI-powered search and photo
  filters."
- **Release notes:** "Version 5.0: Added AI search feature — search your
  photos by content like 'beach' or 'birthday'. New color filters. Fixed
  login issues on Android 13."

Pipeline shape: `Code Commit → Gradle Build (AAB) → Upload to Play Console → Google Review → Release on Store`
