# ToothWise Frontend Polish Plan

Based on a survey of `frontend/src` (React 18 + CRA, plain CSS, no Tailwind).

## What we found

| Area | Finding | Why it matters |
|---|---|---|
| Component kit | `components/ui/*` (Button, Card, Badge, Modal, Input, Select, Field, PageHeader, EmptyState, StatCard, LoadingState, ConfirmDialog…) exists, but **no page imports any of it**. | Each page restyles its own buttons, cards and empty states, so they don't match. |
| Inline styles | ~105 `style={{…}}` blocks, mostly ScreeningDetail (27), PatientDetail (20), Screening (19), Layout (8). 37 hard-coded hex colors in JSX. | They skip the theme tokens, which is why dark mode needs workarounds. |
| Dark mode | `index.css` uses `[style*="background: #FFFFFF"]` attribute selectors and **193 `!important`** to override inline colors. | Fragile: a single spacing change in an inline style breaks dark mode. |
| CSS size | `index.css` is 4,825 lines in one file, with old and new class families mixed together (`pp2-*`, `sd-*`, `audit6-*`, `dash-*`). | Hard to maintain. Dead rules are likely. |
| Design scale | About 20 different `border-radius` values (8–28px) and 57 different font-size values. | Spacing and shapes look slightly inconsistent from page to page. |
| Breakpoints | 10 different max-width breakpoints (480, 560, 600, 640, 720, 760, 768, 900…). | Layouts shift at uneven widths, so tablet sizes look off. |
| Dialogs | Patient and staff deletes use the browser's `window.confirm` (`Patients.jsx:145`, `Dentists.jsx:163`), even though `ConfirmDialog` exists. | Looks unbranded, and is the most dangerous action in the app. |
| States | Empty states are written by hand three different ways (AuditLog, Dentists, Dashboard). "Screening not found" is bare text (`ScreeningDetail.jsx:195`). Some fetches fail silently (`PatientPortal.jsx:93, 646`). | Users get no feedback or recovery path. |
| A11y | Screen-reader-only text is inlined by hand (`ScreeningDetail.jsx:75`). The image `alt` text is generic ("Screening"). | Needs a shared `.sr-only` class and meaningful alt text. |

## Phases

### Phase 1: Design tokens and foundations (≈1 day)
1. Add scale tokens to `:root` in `index.css`:
   - radius: `--r-sm 8 / --r-md 12 / --r-lg 16 / --r-xl 24 / --r-pill 999`
   - spacing: `--s-1 … --s-8` (4px base)
   - type: `--fs-xs 12 / sm 13 / base 15 / md 17 / lg 20 / xl 24 / 2xl 32`
   - elevation: `--shadow-sm / md / lg`
2. Standardize breakpoints to **480 / 640 / 768 / 900 / 1024** and fold the stray ones into those. Keep 900, because it's the sidebar → drawer switch and `MOBILE_BREAKPOINT` in `tokens.js` must match it. *(Done.)*
3. Add utility classes: `.sr-only`, `.stack`, `.row`, `.muted`, `.truncate`.
4. Rename `tokens.js` keys to their meaning (`burgundy` → `text`, `rose` → `accent`) so the JS matches the CSS variables.

### Phase 2: Bring the UI kit into use (≈2 days)
1. Review and finish each `components/ui/*` component against the tokens. Add button variants and sizes, a loading state, and icon slots.
2. Migrate one page at a time, most visible first:
   **Dashboard → Patients → PatientDetail → Screening → ScreeningDetail → Dentists → AuditLog → PatientPortal**.
   For each page: swap ad-hoc buttons, cards, badges and empty states for kit components, and move inline styles into classes.
   - [x] **Dashboard.** Uses PageHeader, StatCard, EmptyState and Button. Added an error state with Retry; before this, a failed load showed the skeleton forever. Quick actions are now real `<button>`s.
   - Kit fixes made along the way: defined the CSS variables the kit relied on but were never set (`--tw-radius-*`, `--tw-space-*`, `--tw-duration-*`…), tokenized the dark-mode colors for buttons and empty states, merged the three copies of `.tw-state`, and declared `prop-types` as a dependency.
   - [x] **Patients.** Now uses the kit's `Modal` and `ConfirmDialog` (rebuilt on the `tw6-modal` styles with portal, Esc, focus trap, focus restore and a busy state), plus EmptyState, Button and PageHeader. Changes:
     - Separate empty states for "no patients", "no search matches" and "load failed".
     - A clear button on search, Esc to clear, and a `/` shortcut hint.
     - Late search responses are ignored, and the list no longer loads twice on mount.
     - Form labels are linked to their inputs, errors use `aria-describedby`, and focus moves to the first invalid field.
     - The Address column hides when the table card is narrow, and the mobile cards follow dark mode.
     - Inline styles went from 28 to 1 (a `--stagger-index` variable).
   - [x] **Dentists (Staff).** Uses Modal, ConfirmDialog, FormField, SearchField and Badge pills. Changes:
     - Deactivating an account now asks for confirmation.
     - The duplicated "Password *" label is gone, and every icon button has a label.
     - Email moved under the name so the Actions column fits.
     - The reset-password header (`tw6-modal-target`) is now styled; it had no CSS before.
   - [x] **PatientDetail.**
     - 404 and network errors are told apart.
     - A failed history or trend request no longer blanks the whole page.
     - Data resets when moving from one patient to another.
     - History rows are real buttons, and there's a shared `RiskBadge`.
   - [x] **Screening (upload).**
     - Step indicator, keyboard-accessible drop zone, and a drag highlight that no longer flickers.
     - The patient's name is shown, and the "AI unavailable" notice appears up front.
     - Analysis overlay, plus a result summary with risk and finding count.
     - The size limit text was fixed: it said 10 MB, validation allows 15 MB.
   - [x] **ScreeningDetail.**
     - The image area shows a loading state instead of "No image data".
     - Not-found and error states, and a model-comparison error with Retry.
     - The detection-view tabs follow the ARIA tabs pattern, with arrow keys.
     - A colour legend, a labelled note box with a character counter and Ctrl+Enter to save, and canvas labels that stay on-canvas.
   - [x] **AuditLog.**
     - The filter now covers all 18 backend actions, grouped (it had 9).
     - Readable action labels, client-side search, and separate error and empty states.
   - [x] **PatientPortal.**
     - Split into `pages/portal/{AuthForms,PortalHome,PortalScreening}.jsx`.
     - History error state, fallback for failed thumbnails, and cards that are real buttons.
     - The open screening is kept in the URL, so the browser Back button works.
     - Focus moves to the heading on open, and the recommendation sort no longer mutates state.
   - Shared pieces added: `ui/FormField`, `ui/SearchField`, `ui/RiskBadge`, `ui/Badge tone=…`, and `components/DetectionCanvas`, which the staff and patient views share.
   - Global fixes:
     - The skeleton shimmer and empty states now follow dark mode.
     - The 404 page spacing is fixed.
     - The `dark-mode` class no longer leaks onto public pages after sign-out.
     - `PasswordField` uses theme tokens.
   - Result: no `window.confirm` left, one hex colour left in pages (from about 37), and inline styles down from about 105 to 15. The remaining 15 are mostly CSS-variable hooks like `--stagger-index`.
3. ~~Replace both `window.confirm` calls~~ (done) with `ConfirmDialog` (danger variant, with the patient or staff name shown).
4. Use `EmptyState` and `LoadingState` / `Skeleton` everywhere. Add an error state with a **Retry** button.

### Phase 3: Clean up dark mode (done)
- Deleted the `[style*=…]` block (61 selectors). Most of them could never match, because React writes inline styles through the DOM and browsers serialize colours as `rgb(…)`.
- Cut the `body.dark-mode` rules from 163 to 24. Most targeted classes nothing renders any more, or public and portal pages that are light-only now that the leak is fixed.
- Sidebar: moved its colours from Layout inline styles into `--sb-*` tokens and `.tw-sb-*` classes, so dark mode is just a variable swap. This replaced a three-layer `!important` chain (inline → `--tw-navy-dark !important` → `#3D1F28 !important`).
- Mobile card tables: they no longer need `!important`, because the selectors are specific enough to outrank the desktop table rules.
- `!important` went from 189 to 104. What's left is mostly the landing-page CSS and the Layout mobile rules that still fight inline layout styles, both covered by the Phase 5 CSS split.
- Checked the dashboard, Patients (desktop and mobile cards), Staff and the drawer in both themes. Public pages stay light after leaving the staff area.

### Phase 4: Page-level polish (done)
Most of the per-page items were handled during the Phase 2 rewrites: Patients, Screening, ScreeningDetail and PatientPortal. This phase covered the rest.
- **Layout.**
  - One route table now drives the document title, the description and the breadcrumbs, so the screening routes are fixed.
  - The top bar shows the trail *to* the page ("CodiSmile Clinic / Patients"); on mobile this becomes a "‹ Patients" back link.
  - Each page's title is now its single `<h1>`, so the name no longer appears twice.
  - Mobile drawer: focus moves into it, Tab stays inside, and Esc returns focus to the menu button.
- **Logo.** Added 96 px and 192 px PNG and WebP variants, used by `LogoMark` and the chat avatar. The 351 KB source logo is now 9 KB (WebP) or 16 KB (PNG) where these components use it.
- **Print.** `@media print` hides the sidebar, top bar, buttons and the note form, and keeps cards together, so a screening result prints cleanly.
- **Staff login.** Email field focused on load, an inline error banner instead of toast-only messages, focus on the field that failed, and `aria-describedby` on errors.
- **Not done here:** `Landing.jsx` has uncommitted edits from outside this work, so it was left alone. It still loads the full 351 KB logo in two `<img>` tags, and the hero `<img>` has no `width`/`height`. Swap in `/codismile/codismile-logo-96.png` and add dimensions once those edits are committed.

### Phase 5: Motion, accessibility and CSS split (done)
- **Motion.**
  - Every `transition` duration now uses `--dur-fast`, `--dur` or `--dur-slow` (62 declarations normalized).
  - The global reduced-motion rule now also zeroes animation and transition delays (staggered rows used to wait up to about 800 ms) and turns off smooth scrolling.
- **Focus.** Every rule that removes an outline has a replacement border or ring. Modals and the mobile drawer trap focus and close with Esc.
- **Contrast (WCAG AA).**
  - Found a second `:root` block in `03-design-overrides.css` that silently redefined the light palette. Folded it into `00-tokens.css`, so there is now one source of truth with no visual change.
  - Using the real palette:
    - Muted text is 5.9:1.
    - Danger is now `#B33A45` (4.95:1 on its tint, was 3.85:1).
    - A new `--tw-accent-text` (`#9E5A55`, 4.9:1) is used wherever the 3.45:1 brand teal was used for text.
    - Placeholders now use the muted colour (were 2.05:1).
  - Dark mode already passed everywhere.
- **Dead CSS.** Removed 887 rules that can never match: superseded designs such as `pp-*`, `tw-modal-v5`, `hero-v2`, `landing-v5`, `clinic-*` and the old `auth-*`. That's 5,163 → 3,466 lines, and the gzipped CSS went from 36 KB to 21 KB.
- **Split.** `index.css` is now an ordered `@import` list of 13 files in `src/styles/` (`00-tokens` … `12-print`). Each file is a contiguous chunk, so the cascade order is unchanged.
- **Verification.** Compared computed styles (20 properties, every element) against the pre-prune stylesheet on landing, login, portal, privacy, 404, all 7 staff routes in light and dark, an open dialog, and 4 routes at 375 px. The only difference is the sidebar background going back to its original `#352126`. A control run with an empty stylesheet flagged every element, so the comparison is sensitive.
- **Not done.** No Lighthouse run (it isn't installed here). About 100 `!important`s remain, mostly in the landing CSS (`07-landing.css`) and in the Layout mobile rules that fight its inline layout styles.

### Follow-ups after Phase 5 (done)
- **Reduced-motion fix.** The Phase 5 duration normalizer had also rewritten `transition-duration: .001ms` inside six reduced-motion blocks to `var(--dur-fast)`, so reduced-motion users still got 120 ms transitions. Restored them to `.001ms`.
- **Layout without inline styles.** `Layout.jsx` now uses `.tw-shell` / `.tw-sb-*` / `.tw-topbar` classes; only `--sidebar-w` stays inline. Its mobile rules no longer need `!important`. Computed styles were identical before and after for the full and rail sidebar in both themes, and for mobile with the drawer closed and open.
- **`!important` down to 16.** That's from 189 at the start; the remaining 16 are reduced motion, print, and the global input focus ring. Removing the others surfaced two rules that had only ever lost to an `!important`: a stale duplicate mobile popover position (deleted) and the landing highlights' `:nth-child(even)` border (now matched by specificity). The chat status dot got a scoped margin rule. Computed styles were re-verified identical on landing (375 and 1280 px), login, portal, the dashboard and patients pages at both widths, and the open popovers.

### Lighthouse audit (done)
Lighthouse 12 was run against the production build served with gzip, on the public pages at 390 px (mobile, simulated slow 4G) and 1440 px (desktop). The staff pages need a signed-in session and the backend, so Lighthouse couldn't reach them.

| Page | Width | Perf | A11y | Best practices | LCP |
|---|---|---|---|---|---|
| Landing | 1440 | 99 | 100 | 100 | 0.8 s |
| Landing | 390 | 83 | 100 | 100 | 4.0 s |
| Login | 1440 | 100 | 100 | 100 | 0.7 s |
| Login | 390 | 92 | 100 | 100 | 2.9 s |
| Patient portal | 1440 | 100 | 100 | 100 | 0.7 s |
| Patient portal | 390 | 91 | 100 | 100 | 3.0 s |

CLS was 0 on every page.

Fixes:
- **Code splitting.** Routes are lazy-loaded behind a `Suspense` fallback, which takes the main bundle from 231 KB to 95 KB gzipped. Staff pages and recharts now load in their own chunks.
- **Fonts.** Google Fonts no longer block rendering (preload, then swap to stylesheet, with a `<noscript>` fallback), and `<meta charset>` is now first in `<head>`.
- **Images.**
  - The hero, location, service and logo images are served as WebP through `<picture>`. That's 1,269 KB of photo JPEGs reduced to 810 KB.
  - The hero image gets `fetchpriority="high"`.
  - `sizes` matches the 1024 px single-column breakpoint.
- **Contrast.** The nav brand subtitle (3.1:1) and footer copyright (4.36:1) now pass.
- **Brand link name.** The `aria-label` now matches the visible text, so it no longer mismatches on desktop or leaves the link unnamed on mobile.

Left as-is:
- Mobile landing LCP is about 4 s, because the hero photo sits below the headline and is discovered by JS. Preloading it would need a landing-only tag in the shared `index.html`.
- Lighthouse still reports about 40 KB of unused JS and about 20 KB of unused CSS in the shared bundle.

### Staff-page accessibility audit (done)
Lighthouse can't reach the signed-in screens, so I ran axe-core 4.14 (the copy bundled with Lighthouse) in the dev build with stubbed data. Tags: WCAG 2.0/2.1 A and AA, plus best-practice. Coverage: all 8 staff routes (including a not-found screening) and 5 dialogs (patient form, staff form, delete confirmation, reset password), each in light and dark mode.
- **Found:** heading order. Pages open with an `<h1>`, but section, dialog and empty-state titles were `<h3>`.
- **Fixed:** those titles are now `<h2>`, and the modal CSS selector accepts both.
- **Checked:** computed heading styles are identical before and after.
- **Re-run:** zero violations everywhere.

## Suggested order and checkpoints
1. Phase 1 → visual check, should be no change.
2. Phase 2 one page at a time, one commit per page, screenshot before and after in both themes.
3. Phase 3 only once grepping for `style={{` with hex colors comes back empty.
4. Phases 4 and 5.

**Done when:** every page builds on the `components/ui` kit, no hex colors in JSX, `!important` under 20, no `window.confirm`, and every page has loading, empty and error states.
