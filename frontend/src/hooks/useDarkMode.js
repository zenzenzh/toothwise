import { useState, useEffect, useCallback } from 'react';

const THEME_KEY = 'tw_theme';

function getInitialTheme() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {}
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function useDarkMode() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.body.classList.toggle('dark-mode', theme === 'dark');
    try { localStorage.setItem(THEME_KEY, theme); } catch {}
  }, [theme]);

  // Dark mode belongs to the staff workspace only. Without this, signing
  // out (or any client-side navigation out of Layout) left the class on
  // <body> and rendered the light-only public/portal pages half-dark.
  useEffect(() => () => document.body.classList.remove('dark-mode'), []);

  const toggle = useCallback(() => setTheme(t => t === 'dark' ? 'light' : 'dark'), []);

  return { isDark: theme === 'dark', toggle };
}
