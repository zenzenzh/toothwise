import { createContext, useContext, useEffect, useState } from 'react';
import { authAPI } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [dentist, setDentist] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tw_dentist')); } catch { return null; }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const clearStaffSession = () => setDentist(null);
    window.addEventListener('tw:patient-session-started', clearStaffSession);
    const onStorage = (event) => { if (event.key === 'tw_patient_token') clearStaffSession(); };
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('tw:patient-session-started', clearStaffSession); window.removeEventListener('storage', onStorage); };
  }, []);

  async function login(email, password) {
    setLoading(true);
    try {
      const { data } = await authAPI.login({ email, password });
      // A browser can only have one active workspace at a time. Clear the
      // patient session before exposing the staff workspace, including the
      // in-memory patient state through the cross-context event.
      localStorage.removeItem('tw_patient_token');
      localStorage.removeItem('tw_patient');
      window.dispatchEvent(new Event('tw:staff-session-started'));
      localStorage.setItem('tw_token', data.access_token);
      localStorage.setItem('tw_dentist', JSON.stringify(data.dentist));
      setDentist(data.dentist);
      return data;
    } finally { setLoading(false); }
  }

  function logout() {
    localStorage.removeItem('tw_token');
    localStorage.removeItem('tw_dentist');
    setDentist(null);
    window.dispatchEvent(new Event('tw:staff-session-ended'));
  }

  return <AuthContext.Provider value={{ dentist, login, logout, loading }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
