// Centralized timestamp formatting for the whole app.
//
// The backend stores every timestamp in UTC (see backend/app/models.py).
// Passing an ISO string straight into toLocaleString()/toLocaleDateString()
// without an explicit `timeZone` silently uses the BROWSER's own system
// timezone, not the clinic's - a browser set to any timezone other than
// Asia/Manila would show the wrong time. The 'en-PH' locale only affects
// formatting conventions (date order, comma placement); it does NOT imply
// or set a timezone. Every call site in this app should go through these
// helpers instead of calling toLocaleString()/toLocaleDateString() directly,
// so the whole system stays consistent without ever manually adding +8.

const PH_TZ = 'Asia/Manila';
const PH_LOCALE = 'en-PH';

export function formatDateTimePH(isoString, opts = {}) {
  if (!isoString) return '';
  return new Date(isoString).toLocaleString(PH_LOCALE, {
    timeZone: PH_TZ,
    dateStyle: 'medium',
    timeStyle: 'short',
    ...opts,
  });
}

export function formatDatePH(isoString, opts = {}) {
  if (!isoString) return '';
  return new Date(isoString).toLocaleDateString(PH_LOCALE, {
    timeZone: PH_TZ,
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    ...opts,
  });
}

export function formatShortDatePH(isoString) {
  if (!isoString) return '';
  return new Date(isoString).toLocaleDateString(PH_LOCALE, {
    timeZone: PH_TZ,
    month: 'short',
    day: 'numeric',
  });
}

export function formatTimePH(isoString) {
  if (!isoString) return '';
  return new Date(isoString).toLocaleTimeString(PH_LOCALE, {
    timeZone: PH_TZ,
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

// Converts a UTC ISO timestamp into the "YYYY-MM-DDTHH:mm" shape a
// <input type="datetime-local"> needs, using Asia/Manila wall-clock time -
// not the browser's own timezone. Reading .getFullYear()/.getHours() etc.
// directly off a Date object gives the BROWSER's local components, which
// silently produces the wrong prefilled time on a browser set to any other
// timezone; Intl.DateTimeFormat with an explicit timeZone avoids that.
export function toManilaInputValue(isoString) {
  if (!isoString) return '';
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: PH_TZ,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(isoString));
  const get = (type) => parts.find(p => p.type === type)?.value;
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`;
}

// Inverse of toManilaInputValue: takes the naive "YYYY-MM-DDTHH:mm" string
// out of a <input type="datetime-local"> - understood as Asia/Manila wall
// time, since that's what was prefilled into it - and returns the correct
// UTC ISO string to send to the API.
//
// A fixed +08:00 offset is reliable here specifically because the
// Philippines does not observe daylight saving time; this would NOT be
// safe for a timezone with DST transitions. Passing the naive string
// straight to `new Date(...)` instead would have JS interpret it as the
// BROWSER's own local time, silently double-converting or mis-converting
// it whenever the browser isn't already set to Asia/Manila.
export function manilaInputValueToUTCISOString(localValue) {
  if (!localValue) return null;
  return new Date(`${localValue}:00+08:00`).toISOString();
}

// ---------- Birthdate / age helpers (patient registration) ----------
//
// These mirror the backend's own rules exactly (see
// backend/app/schemas.py: _validate_birthdate and backend/app/models.py:
// Patient.age) so the form can give immediate feedback, but the backend
// re-validates and recomputes independently - age is never trusted from
// the client, and a future or implausible birthdate is rejected server-
// side regardless of what the form allowed through.

const PATIENT_MAX_AGE_YEARS = 120;

export function todayISODate() {
  // Local calendar date for a <input type="date"> max attribute. A plain
  // date (no time-of-day) has no meaningful timezone component, so this
  // intentionally does not go through the Manila-specific helpers above.
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function minBirthdateISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear() - PATIENT_MAX_AGE_YEARS}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// Computed only for immediate display in the form - the value that's
// actually stored and used anywhere else in the app always comes from
// the backend's own Patient.age property, computed from the stored
// birthdate at request time.
export function calculateAge(birthdateISO) {
  if (!birthdateISO) return null;
  const birth = new Date(birthdateISO + 'T00:00:00');
  if (Number.isNaN(birth.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const hasHadBirthdayThisYear =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());
  if (!hasHadBirthdayThisYear) age -= 1;
  return age >= 0 ? age : null;
}
