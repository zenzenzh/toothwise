// Semantic color tokens for inline styles. Each maps to a CSS variable in
// index.css, so values follow the active theme (light / dark) automatically.
// Prefer CSS classes over inline styles; use these only when a style must be
// computed in JS.
const T = {
  text: 'var(--tw-text)',
  muted: 'var(--tw-muted)',
  accent: 'var(--tw-teal)',
  accentText: 'var(--tw-accent-text)',
  accentStrong: 'var(--tw-teal-dark)',
  bg: 'var(--tw-bg)',
  surface: 'var(--tw-surface)',
  surfaceAlt: 'var(--tw-surface-alt)',
  border: 'var(--tw-border)',
  danger: 'var(--tw-danger)',
  dangerBg: 'var(--tw-danger-bg)',
  dangerBorder: 'var(--tw-danger-border)',
  warning: 'var(--tw-warning)',
  warningBg: 'var(--tw-warning-bg)',
  warningBorder: 'var(--tw-warning-border)',
  success: 'var(--tw-success)',
  successBg: 'var(--tw-success-bg)',
  successBorder: 'var(--tw-success-border)',
  indigo: 'var(--tw-indigo)',
  indigoBg: 'var(--tw-indigo-bg)',
};

// Must match the 900px sidebar → drawer @media rules in index.css.
export const MOBILE_BREAKPOINT = 900;

export default T;
