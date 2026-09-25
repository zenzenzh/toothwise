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

  const toggle = useCallback(() => setTheme(t => t === 'dark' ? 'light' : 'dark'), []);

  return { isDark: theme === 'dark', toggle };
}
