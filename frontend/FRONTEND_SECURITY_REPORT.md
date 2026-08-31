# ToothWise Frontend — Security Hardening Pass

Scope: `frontend/` only (React 18 + react-router-dom v6 + axios, CRA/react-scripts,
inline-style components, no TypeScript, no CSS framework). No backend code was
changed. Auth: JWT bearer tokens in `localStorage`, attached via an axios request
interceptor (two separate token/session pairs — staff `tw_token`/`tw_dentist` and
patient-portal `tw_patient_token`/`tw_patient` — so a staff and patient session
can coexist in the same browser without colliding).

## STEP 1 — What was inspected

- `package.json` / `package-lock.json` — react 18.2, react-router-dom 6.21,
  axios 1.6.5, react-hot-toast, react-webcam, recharts. No security-specific
  libraries were present or added; no `dangerouslySetInnerHTML`, no `eval`.
- `src/api/index.js` — the single centralized axios client (two instances:
  staff + patient), request/response interceptors, error normalization.
- `src/context/AuthContext.jsx`, `src/context/PatientAuthContext.jsx` — session
  state, login/register/logout.
- `src/App.jsx` — routing table and the `Protected` route guard.
- Every page in `src/pages/`: `Login.jsx`, `PatientPortal.jsx`, `Dashboard.jsx`,
  `Patients.jsx`, `PatientDetail.jsx`, `Screening.jsx`, `ScreeningDetail.jsx`,
  `Dentists.jsx`, `Appointments.jsx`, `AuditLog.jsx`.
- `src/components/Layout.jsx` (nav / route shell).
- Searched the whole `src/` tree for `dangerouslySetInnerHTML`, `eval(`,
  `console.*`, `localStorage`/`sessionStorage`, and `window.location`.

No `.env` file / `process.env.REACT_APP_*` usage was found in the frontend —
the API base URL is derived at runtime from `window.location.hostname`
(`src/api/index.js`), so there's nothing sensitive baked into a build-time
environment variable to audit here.

## STEP 2 & 3 — Findings, plan, and fix

| Severity | Issue | File | Risk | Fix | Verified |
|---|---|---|---|---|---|
| High | Staff login form shipped with a **real admin email + password pre-filled** in component state (`configured admin credentials`) | `pages/Login.jsx` | Anyone who opens the page source, dev tools, or the JS bundle gets a working admin credential | Removed; both fields now start empty | Yes |
| Medium | Patient self-registration accepted **any string** as email/phone (only HTML `type="email"` + a bare `required`), password only required 6 characters with no complexity | `pages/PatientPortal.jsx` | Junk contact info breaks appointment confirmations (email/SMS); weak passwords are easier to brute-force once past any rate limiting | Added `validateEmail`, `validatePHMobile`, and an 8-char + upper/lower/number `validatePassword` policy with a live checklist; added a confirm-password field | Yes |
| Medium | Admin-created dentist accounts and password resets had the same 6-character-only rule, no email format check | `pages/Dentists.jsx` | Weak staff credentials on accounts with clinical/admin privileges | Same shared `validateEmail` / `validatePassword` policy applied to both the "Add Dentist" and "Reset Password" forms | Yes |
| Medium | FastAPI 422 validation errors return `detail` as an **array of `{loc, msg, type}` objects**, but the UI passed `err.response?.data?.detail` straight into `toast.error(...)` across 5 pages — renders as `[object Object]` instead of a message, and risks echoing raw field paths | `api/index.js`, `Patients.jsx`, `Dentists.jsx`, `Appointments.jsx`, `PatientPortal.jsx` | Confusing/unsafe error surface; borderline information disclosure of internal field names | Centralized `friendlyErrorMessage()` now explicitly handles 400/401/403/404/422/429/500+network, extracts only the human `msg` text from 422 arrays, and every page now uses `err.friendlyMessage` instead of reaching into the raw response | Yes |
| Low | `localStorage.clear()` on the staff 401-interceptor and on staff logout wiped **both** staff and patient session keys, even though they're deliberately separate | `context/AuthContext.jsx`, `api/index.js` | A dentist logging out (or hitting a 401) could silently log out a patient session active in the same browser tab set | Changed to `removeItem` on only the relevant session's keys, on both the staff and patient axios instances | Yes |
| Low | Patient-portal 401 redirect targeted `/portal`, but the actual route (per `App.jsx`) is `/patient-portal` | `api/index.js` | A session-expiry redirect would land on a route that doesn't exist instead of the login screen | Corrected to `/patient-portal` in both the redirect and the "are we already on the login page" check | Yes |
| Low | No client-side validation on dental-image uploads before sending to the backend — any file type/size was accepted by the picker | `pages/Screening.jsx` | Poor UX (large/garbage files fail late, after a slow upload); relied entirely on the backend for this | Added `validateImageFile()`: rejects empty files, files >15MB, and non-JPEG/PNG/WEBP MIME types, with a friendly message; also narrowed the `<input accept>` hint | Yes |
| Low | `AuditLog.jsx` had no client-side admin gate (unlike `Dentists.jsx`), so a non-admin hitting the route directly saw a bare toast + empty table instead of a clear "Admin Access Required" state | `pages/AuditLog.jsx` | UX inconsistency only — the backend already rejected the request | Added the same `Admin Access Required` gate pattern used on `Dentists.jsx` | Yes |
| Informational | Several forms (`Patients.jsx` contact/address, `Appointments.jsx` reason/notes, `ScreeningDetail.jsx` clinical notes, all password fields, names, emails) had no `maxLength` | Multiple pages | Minor — allowed pasting oversized input that the backend would reject anyway | Added `maxLength` attributes sourced from one shared `LIMITS` object in `utils/validation.js` | Yes |
| Informational | Password fields had no show/hide control | `Login.jsx`, `PatientPortal.jsx`, `Dentists.jsx` | Accessibility/UX only | Added a reusable, accessible `PasswordField` component (`aria-label`, `aria-pressed` toggle button, never logs or double-stores the value) | Yes |

### Verified already correct — left unchanged

- **No `dangerouslySetInnerHTML` or `eval`** anywhere in `src/`. All user-controlled
  text (patient names, notes, audit log details, recommendation text) is rendered
  through normal JSX interpolation, which HTML-escapes by default.
- **No open-redirect surface** — nothing in the app reads a redirect target from a
  query string or reflects a user-controlled URL into `href`/`src`/`window.location`.
  (Added `isSafeInternalPath()` to `utils/validation.js` as a guard for future use,
  since none currently exists to fix.)
- **Protected routes** (`App.jsx`'s `Protected` wrapper) correctly gate the staff
  app behind `dentist` state, and login-only/portal-only routes are excluded from
  the auth-redirect logic to avoid loops.
- **Screening/patient records are fetched by ID from the URL** (`/screenings/:id`,
  `/patients/:id`) with no independent frontend authorization check — this is
  correct, since the frontend cannot safely make that decision; both
  `PatientDetail.jsx` and `ScreeningDetail.jsx` already show a clean "not found"
  state on a 403/404 rather than assuming success.
- **Dental images and the PDF report** are fetched through authenticated
  `api.get(..., { responseType: 'blob' })` calls (never a plain public `<img src>`
  or `<a href>`), converted to object URLs, and revoked on unmount — already
  correct and left as-is.
- **No secrets in the frontend** — no API keys, DB credentials, or JWT signing
  material anywhere in `src/`.
- **Console logging** — only a single non-sensitive `console.warn('Torch
  constraint failed', err)` in `Screening.jsx`; nothing logs tokens, passwords,
  or patient data.

## STEP 4/5 — Implementation & testing

New shared modules:
- `src/utils/validation.js` — `validateEmail`, `validatePHMobile`,
  `passwordRequirements`/`validatePassword`, `validateRequiredText`/
  `validateOptionalText`, `validateImageFile`, `isSafeInternalPath`, and the
  `LIMITS` constants used for every `maxLength`.
- `src/components/PasswordField.jsx` — accessible password input with
  show/hide toggle and an optional live requirements checklist.

`npm install && npm run build` completes successfully (`Compiled with
warnings` — the warnings are pre-existing ESLint `no-unused-vars` /
`exhaustive-deps` notices unrelated to this pass, not build failures).

Manually exercised (dev environment, non-destructive):
- Empty / malformed / overlong email and password on both login forms →
  inline errors, no request sent.
- Mismatched confirm-password on patient registration and dentist password
  reset → blocked client-side with a clear message.
- Junk phone numbers (`asdf`, `12345`) on patient registration → rejected
  with a PH-mobile-format message; valid `09XXXXXXXXX` / `+639XXXXXXXXX`
  accepted.
- Oversized / wrong-type file picked for a screening upload → rejected
  before any network request.
- Simulated 401/403/404/422/429/500 responses → each produces the intended
  generic, non-leaking message from `friendlyErrorMessage()`.
- Non-admin session navigating directly to `/audit-log` and `/dentists` →
  consistent "Admin Access Required" panel on both.

## Backend dependencies (must be enforced server-side — the frontend cannot)

- Actual password hashing, complexity re-validation, and rate limiting on
  auth endpoints.
- Independent re-validation of email format/uniqueness and phone format —
  the frontend's checks are UX only and are trivially bypassed by calling
  the API directly.
- File content/signature/size validation for uploaded images (not just
  MIME type, which the browser self-reports).
- All authorization (IDOR/BOLA) checks on `/patients/:id`,
  `/screenings/:id`, `/appointments`, `/audit-logs`, and the image/PDF
  endpoints.
- CORS restricted to the actual frontend origin(s).
- JWT signing/verification, secrets, and database credentials.

## Remaining risks (not changed in this pass)

- **JWT in `localStorage`** — unchanged, as before: this is an XSS-risk
  tradeoff, not something this pass introduced or fixed. Given no
  `dangerouslySetInnerHTML`/`eval` exists in the codebase today, the
  practical exposure is low, but it remains a future httpOnly-cookie
  migration item, and it is not "fixed" by anything in this report.
- **CSP / clickjacking headers** — these belong at the server/reverse-proxy
  layer; nothing in the React app can enforce them. The codebase itself
  has no inline scripts/handlers and would not block a strong CSP if one
  is added server-side.
- **Password policy strength** — 8 chars + upper/lower/number is a
  reasonable capstone-level baseline, not an exhaustive policy (no
  breached-password check, no rate-limited lockout enforced from this
  layer — that's backend work).

## Recommendations for next phase

1. Mirror the same email/phone/password validation rules server-side if
   they aren't already 1:1 (frontend checks are UX-only).
2. Consider httpOnly-cookie auth if/when the architecture allows it.
3. Add CSP / `X-Frame-Options`/`frame-ancestors` at the reverse proxy.
4. Add automated tests around the new validators (`utils/validation.js`)
   since they're now the single source of truth for several forms.

**This frontend is not "100% secure."** This pass fixed the issues listed
above and documents what was inspected, changed, and tested. Authentication,
authorization, database access, SQL-injection prevention, file-content
validation, rate limiting, secrets, and patient-data access all remain the
responsibility of the FastAPI backend, which the frontend cannot substitute
for.
