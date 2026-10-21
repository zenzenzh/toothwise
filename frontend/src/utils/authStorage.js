// Where sign-in sessions are kept.
//
// "Remember me" sessions go in localStorage, so the device stays signed in
// after the browser is closed. Other sessions go in sessionStorage, which
// the browser clears when the window closes. Reads check both places, and
// every write clears the other place first so a key never exists twice.

function safe(fn, fallback = null) {
  try { return fn(); } catch { return fallback; }
}

export function getAuthItem(key) {
  return safe(() => sessionStorage.getItem(key)) ?? safe(() => localStorage.getItem(key));
}

export function setAuthItem(key, value, remember) {
  removeAuthItem(key);
  const store = remember ? localStorage : sessionStorage;
  safe(() => store.setItem(key, value));
}

export function removeAuthItem(key) {
  safe(() => sessionStorage.removeItem(key));
  safe(() => localStorage.removeItem(key));
}

// Whether the current session for this token key was saved with "remember me".
export function isRemembered(key) {
  return safe(() => localStorage.getItem(key) !== null, false);
}

export function readAuthJSON(key) {
  return safe(() => JSON.parse(getAuthItem(key)));
}
