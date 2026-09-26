# Toothwise — Frontend Design Critique (Impeccable / Craft-floor)

Mode: Operate (dashboard / clinical task flow). Source of truth: `DESIGN.md` + `frontend/src/index.css` + `Layout.jsx` + `AuditLog.jsx`.

Scoring: 0 (fail) / 3 (pass) / 5 (outstanding). Ceiling = full cycle (inspection + one remediation pass + confirm).

---

## 1. Color / Dark Mode — 3/5 (mixed pass, significant gaps)

Evidence: 143 `body.dark-mode` selectors in `index.css`. Dark palette is defined (`#0F1117` bg, `#181B23` surface, `#F0F0F3` text, `#3D1F28` dark-pink sidebar).

Defects:
- **Sidebar** (Layout.jsx line ~105): inline `background: '#352126'` overrides the CSS `#3D1F28` because inline > stylesheet. The `!important` rule added to index.css hasn't fully won — verify rendered color.
- **Audit log** (`audit6-table-card`): hardcoded `#FFFFFF` / `#E5DADC` was overridden with `!important`, but `tw-page-title-wrap h2` hardcoded `#4B2F35` is only partially overridden; page headers could still render dark-ink in dark mode.
- **Topbar** (post-last-edit): set to `#000000` with white text and icon hover states — passes contrast.
- **Phantom tokens** (`--tw-ease-out`, `--tw-duration-*`, `--tw-ease-spring`) remain undefined across the whole app — no crash, but design system is incomplete.

Fix batch: (a) remove or replace the `#352126` inline style in Layout.jsx with a class-driven color; (b) verify `audit6-table-card` renders with `var(--tw-surface)` after build; (c) define missing ease/duration tokens or strip references.

---

## 2. Typography / Hierarchy — 2/5

Evidence: `tw-page-title-wrap h2` = 26px / 700; `.tw-page-title` from Layout = 17px (mobile override 17px); body measure not explicitly set; `tw-page-header` uses flex, no baseline rhythm.

Defects:
- **No body measure defined** — craft-floor requires 65–75ch for readability; the app relies on Tailwind defaults, not the design system.
- **No tracking / leading floor** — headings lack the `-0.04em` tracking floor for large display; `line-height: 1.15` on `h2` is acceptable but not part of a scale.
- **Eyebrow removed** (Layout.jsx edit) — good (craft-floor bans eyebrow kickers above headings); the heading now carries its own weight. Confirmed.
- **No font-family declaration** in tokens / CSS — the palette defines colors, not typography. Risk: system falls back to browser defaults instead of a clinical/medical typeface.

Fix batch: add `font-family` to tokens / body; set a `max-width` / measure constraint on `.tw-content`; enforce heading scale (display / h1 / h2 / h3 / body / small) in `index.css` rather than scattered inline styles.

---

## 3. Spacing / Layout — 2/5

Evidence: `tw-page-layout` gap 24px; topbar height 66px (mobile 66px); content uses `padding: 28px 32px`; sidebar collapsed/expanded handled with CSS class; `tw-main` flex layout.

Defects:
- **Inconsistent gap rhythm** — page header gap 12px, content gap 24px, sidebar gap varies (no token); craft-floor requires tight groups with generous separation and “more space above a heading than below it”. The header (`tw-page-header`) has no bottom margin defined; the page title sits flush above content.
- **Card uniformity risk** — audit log uses `audit6-table-card` (rounded 18px, shadow); other pages (Dashboard, Screening) use different card structures. No shared card token for radius, shadow, border.
- **No responsive breakpoint tokens** — all responsiveness is hardcoded in `@media` with pixel values; no fluid spacing scale.

Fix batch: define spacing tokens (`--tw-space-xs: 4px`, `--tw-space-sm: 8px`, ... `--tw-space-xl: 32px`) and replace hardcoded `gap: 24px` / `padding: 28px` with token references; enforce consistent card shell (radius 18px, shadow `0 18px 50px rgba(0,0,0,.5)`, border `var(--tw-border)`).

---

## 4. Component Quality / States — 2/5

Evidence: Skeleton, ConfirmDialog, Modal, EmptyState, StatCard all exist; Badge, ChatWidget present.

Defects (from files reviewed):
- **Skeleton** (`Skeleton.jsx`): was converted to CSS vars (good); verify it uses `var(--tw-surface)` for the shimmer base and `var(--tw-border)` for the shimmer gradient — if not, it reads as gray-on-gray in dark mode.
- **EmptyState**: needs dark-mode override for icon/text colors; check `frontend/src/components/ui/EmptyState.jsx` — if it uses hardcoded `#4B2F35`, it fails in dark.
- **StatCard**: converted, but check `StatCard.jsx` for any remaining `#FCE8EA` light-mode danger background that isn't mapped to `var(--tw-danger-bg)`.
- **ConfirmDialog / Modal**: overlays now `rgba(0,0,0,.5)` — correct. But does the dialog content use `var(--tw-surface)` or hardcoded white? Verify the inner card.
- **Badge**: `Badge.jsx` might have inline colors for `danger` / `warning` — verify.

Fix batch: create one `states` audit — hover, disabled, loading, error, empty — per component, in one build-render-check cycle.

---

## 5. Motion / Micro-interaction — 1/5 (missing)

Evidence: no `animation` / `transition` tokens defined; `--tw-ease-out` / `--tw-duration-*` phantom; `useDarkMode` hook present.

Defects:
- **No motion system** — the design is static everywhere. Craft-floor requires “one authored moment, not scattered effects” — at minimum a page-enter fade and hover transitions.
- **Hook only** — `useDarkMode.js` manages theme toggle; no animation wrapper.
- **No reduced-motion guard** — `prefers-reduced-motion` not handled.

Fix batch: add `transition: color .2s ease, background-color .2s ease, border-color .2s ease` to interactive elements (buttons, nav links, cards); add one entrance stagger to `AuditLog.jsx` rows (already has `.stagger-item` class — wire it to a keyframe or `animation-delay` based on index); respect `prefers-reduced-motion: reduce` by disabling animations.

---

## 6. Copy / UX Language — 2/5

Evidence: “Systems operational” pill removed (good, it was misleading); page labels come from router / props; audit log uses `ACTION_COLOR` mapping.

Defects:
- **Audit log labels** (`AuditLog.jsx`): “ACTION_COLOR” uses CSS variables — verify mapping covers all actions; missing actions will render with no color or wrong category.
- **Notification popover** (`Layout.jsx`): “Clinic notifications” / “Actionable activity from your workspace” — copy is generic; clinical context missing. Could reference “screening alerts”, “patient visit updates”.
- **No error / recovery copy** seen in reviewed surfaces — empty states use generic text.

Fix batch: tighten audit action labels; replace notification copy with clinical-context equivalents; confirm all error states (network fail, 503 from detection) have recovery actions.

---

## 7. Coverage / Completeness — 3/5

Evidence: both dark and light modes partially covered; design reference (`DESIGN.md`) exists; PDF, docx, gantt chart, diagram files committed; `tokens.js` converted.

Defects:
- **No design detector run** (`detect.mjs`) — per impeccable skill, after UI edit, run `node .opencode/skills/impeccable/scripts/detect.mjs --json <targets>`. Not done.
- **No PRODUCT.md** — skill requires `init` for new surfaces. This is an existing system (Operate mode), so not blocking, but a shorter PRODUCT.md (one-page context) would ground future refinements.
- **Desktop + mobile not batched** — only a single build-verify cycle was done (desktop via command line). No mobile viewport check.

Fix batch: (a) run detector over `Layout.jsx`, `AuditLog.jsx`, `Dashboard.jsx`, `index.css`, `tokens.js`; (b) build and inspect at 375px / 768px / 1440px (or use Playwright/Chrome if available); (c) fix all findings in one batch; (d) confirm with at most one final rebuild.

---

## 8. Craft / Distinctiveness — 3/5 (better than safe, not exceptional)

Evidence: dark mode has a real palette (plum/pink sidebar, warm navy/teal accents, near-black bg); audit log is a real clinical interface; PDF generator is custom.

Defects (what's missing to earn “award-winning”):
- **No hero / scanning moment** — the dashboard opens directly to data; there's no “first-load” orientation moment for a clinician.
- **No signature graphic or brand mark** — `brandName` / `avatar` are generic; the sidebar could carry a refined logomark rather than just text.
- **Typography is generic** — no serif/sans pairing, no editorial scale; clinical apps often benefit from a high-contrast editorial pair (e.g., a clean sans for UI, a refined serif for headings).
- **No material texture** — everything is flat; subtle paper / surface texture (even a very subtle gradient noise or translucent overlay) would elevate it.

Fix batch (high-impact, bounded):
1. Add a refined typography scale with one display font + one body font, both loaded from Google Fonts / local.
2. Replace sidebar brand area with a minimal geometric mark (tooth-form / cross-form) in `var(--tw-navy)`.
3. Add a very subtle `backdrop-filter: blur(12px)` to the topbar (already near-black) and a refined glass card for the audit log header.
4. Confirm all fixes in one desktop + mobile render pass.

---

## Remediation Plan (one batch, stop after confirm)

**Batch A — mechanical fixes:**
- Layout.jsx: replace `background: '#352126'` inline with class / CSS variable.
- index.css: add ease/duration tokens OR remove phantom references; verify `audit6-table-card` renders.
- Tokens / body: set `font-family`; define measurement constraints.
- All interactive elements: `transition` on hover/focus.
- AuditLog: wire `.stagger-item` animation (with `prefers-reduced-motion` guard).

**Batch B — craft pass (high impact):**
- Add editorial font pair + typography scale.
- Refine sidebar brand mark + topbar glass treatment.
- Build, render desktop + mobile, fix anything the render shows.
- Confirm with at most one rebuild.

**Stop:** after Batch B confirms. No further polish.

---

## References used
- `DESIGN.md` (dark direction, palette)
- `frontend/src/index.css` (tokens, dark rules)
- `frontend/src/components/Layout.jsx` (header, sidebar, pill)
- `frontend/src/pages/AuditLog.jsx` (table card, action colors)
- `frontend/src/tokens.js` (CSS var mapping)
- `reference/craft-floor.md` (contrast, spacing, type, motion, states, coverage)
- Skill: `critique [target]` · base: `C:\Users\zenn\toothwise\.opencode\skills\impeccable`
