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

### Phase 3: Clean up dark mode (≈1 day; needs Phase 2 first)
> Also remove `body.dark-mode .stagger-item:hover { background … !important }` (index.css, around line 169). It highlights any staggered card on hover in dark mode, not just table rows.
1. Once the inline colors are gone, delete the `[style*=…]` override block (around lines 192–260) and most of the `body.dark-mode … !important` rules.
2. Dark mode should come only from swapping variables under `body.dark-mode`.
3. Check contrast (WCAG AA 4.5:1) for muted text, badges and risk pills in both themes.

### Phase 4: Page-level polish (≈2–3 days)
- **Layout and sidebar:** the top-bar title reads "ToothWise" on the screening-result route, because Layout's title map is missing that route. Also, the page title appears twice (in the top bar and again in the page header). Keep one. Also the active-route indicator, collapsed state on tablets, and keyboard focus inside the mobile drawer.
- **Dashboard:** line up the stat cards, give charts the same colors as the risk badges, and replace the "No detection data yet" placeholder.
- **Patients:** sticky table header, row hover and focus styles, a clear search button, and pagination or row count. Turn the table into cards on mobile.
- **Screening (upload):** stronger drag-and-drop highlight, image preview with a remove option, upload progress, and validation messages for file type and size.
- **ScreeningDetail:** a consistent toggle style for the canvas overlay, a legend for detection colors, a print/export-friendly layout, a proper not-found state, and descriptive `alt` text.
- **PatientPortal (732 lines):** split into sub-components, and fix the silent image-load failures with a fallback.
- **Landing:** compress the hero and education images (`public/codismile/*.jpg`) and add `loading="lazy"`, `width` and `height` to prevent layout shift.
- **Forms (Login, staff and patient modals):** inline field errors through `Field`, a disabled or loading submit button, and autofocus on the first field.

### Phase 5: Motion, accessibility and quality checks (≈1 day)
- Use one set of motion tokens (`--ease`, `--dur-fast 120ms`, `--dur 200ms`) and respect `prefers-reduced-motion` everywhere.
- Visible `:focus-visible` rings on every interactive element. Modals trap focus and close with Esc.
- Lighthouse pass (target ≥90 for Accessibility and Best Practices) at 390, 768 and 1440px in both themes. Save screenshots to `frontend/audit-shots/`.
- Split `index.css` into `styles/tokens.css`, `base.css`, `components.css`, `layout.css` and `pages/*.css`, and remove dead selectors.

## Suggested order and checkpoints
1. Phase 1 → visual check, should be no change.
2. Phase 2 one page at a time, one commit per page, screenshot before and after in both themes.
3. Phase 3 only once grepping for `style={{` with hex colors comes back empty.
4. Phases 4 and 5.

**Done when:** every page builds on the `components/ui` kit, no hex colors in JSX, `!important` under 20, no `window.confirm`, and every page has loading, empty and error states.
