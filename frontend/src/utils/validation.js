// Centralized frontend validation.
//
// IMPORTANT: everything here is for user experience only. It reduces
// obviously-bad input (typos, empty fields, junk phone numbers, weak
// passwords) before a request is even sent, but it is NOT a security
// boundary. The FastAPI backend must independently re-validate every one
// of these fields - a browser is fully controlled by the person using it,
// so any of this can be bypassed by calling the API directly.

export const LIMITS = {
  NAME_MAX: 120,
  EMAIL_MAX: 254,
  PASSWORD_MIN: 8,
  PASSWORD_MAX: 72, // bcrypt's hard limit - longer is silently truncated server-side
  PHONE_MAX: 20,
  ADDRESS_MAX: 300,
  NOTES_MAX: 1000,
  REASON_MAX: 200,
  LICENSE_MAX: 50,
};

// Deliberately not a "perfect" RFC-5322 regex - those tend to reject real
// addresses. This just requires text, an @, more text, a dot, and more
// text, with no whitespace. Good enough to catch typos and junk without
// being overly restrictive.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(rawValue) {
  const value = (rawValue || '').trim();
  if (!value) return { valid: false, message: 'Email is required.' };
  if (value.length > LIMITS.EMAIL_MAX) return { valid: false, message: 'Email is too long.' };
  if (/\s/.test(value)) return { valid: false, message: 'Email cannot contain spaces.' };
  if (!EMAIL_RE.test(value)) return { valid: false, message: 'Please enter a valid email address.' };
  return { valid: true, value };
}

// Philippine mobile numbers: 11 digits starting with 09 (e.g. 09171234567)
// or the same number in +63 form (e.g. +639171234567). Strips spaces and
// dashes before checking so "0917 123 4567" and "0917-123-4567" both work.
export function validatePHMobile(rawValue, { required = false } = {}) {
  const trimmed = (rawValue || '').trim();
  if (!trimmed) {
    return required
      ? { valid: false, message: 'Mobile number is required.' }
      : { valid: true, value: '' };
  }
  const digitsAndPlus = trimmed.replace(/[\s-]/g, '');
  if (!/^(\+639\d{9}|09\d{9})$/.test(digitsAndPlus)) {
    return {
      valid: false,
      message: 'Enter a valid PH mobile number, e.g. 09171234567 or +639171234567.',
    };
  }
  const normalized = digitsAndPlus.startsWith('+63')
    ? '0' + digitsAndPlus.slice(3)
    : digitsAndPlus;
  return { valid: true, value: normalized };
}

// Password policy for any account created in ToothWise (staff or patient).
// Mirrors what should also be enforced server-side. Returns which specific
// requirements are unmet so the UI can show a live checklist instead of a
// single opaque error.
export function passwordRequirements(password) {
  const value = password || '';
  return [
    { key: 'length', label: `At least ${LIMITS.PASSWORD_MIN} characters`, met: value.length >= LIMITS.PASSWORD_MIN },
    { key: 'upper', label: 'One uppercase letter', met: /[A-Z]/.test(value) },
    { key: 'lower', label: 'One lowercase letter', met: /[a-z]/.test(value) },
    { key: 'number', label: 'One number', met: /[0-9]/.test(value) },
  ];
}

export function validatePassword(password) {
  const value = password || '';
  if (!value) return { valid: false, message: 'Password is required.' };
  if (value.length > LIMITS.PASSWORD_MAX) {
    return { valid: false, message: `Password must be ${LIMITS.PASSWORD_MAX} characters or fewer.` };
  }
  const unmet = passwordRequirements(value).filter(r => !r.met);
  if (unmet.length > 0) {
    return { valid: false, message: 'Password does not meet the requirements below.' };
  }
  return { valid: true, value };
}

export function validateRequiredText(rawValue, label, max = LIMITS.NAME_MAX) {
  const value = (rawValue || '').trim();
  if (!value) return { valid: false, message: `${label} is required.` };
  if (value.length > max) return { valid: false, message: `${label} must be ${max} characters or fewer.` };
  return { valid: true, value };
}

export function validateOptionalText(rawValue, label, max) {
  const value = (rawValue || '').trim();
  if (value.length > max) return { valid: false, message: `${label} must be ${max} characters or fewer.` };
  return { valid: true, value };
}

// ---------- Image upload validation (dental screening photos) ----------

export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_IMAGE_BYTES = 15 * 1024 * 1024; // 15 MB

export function validateImageFile(file) {
  if (!file) return { valid: false, message: 'Please choose an image to upload.' };
  if (file.size === 0) return { valid: false, message: 'That file appears to be empty. Please choose another file.' };
  if (file.size > MAX_IMAGE_BYTES) {
    return { valid: false, message: 'Image size exceeds the allowed limit (15 MB).' };
  }
  // Note: this only checks the browser-reported MIME type, which a client
  // fully controls - it's a UX convenience, not a security check. The
  // backend independently validates the actual file bytes/signature.
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return { valid: false, message: 'Please upload a supported dental image (JPEG, PNG, or WEBP).' };
  }
  return { valid: true };
}

// ---------- Safe URL / redirect helpers ----------

// Only allow relative, in-app paths for any client-side redirect. Rejects
// absolute URLs and dangerous schemes (javascript:, data:, etc.) so a
// query param or stored value can never send someone off-site.
export function isSafeInternalPath(path) {
  if (typeof path !== 'string' || !path) return false;
  if (!path.startsWith('/') || path.startsWith('//')) return false;
  return !/^\/\s*[a-z][a-z0-9+.-]*:/i.test(path);
}
