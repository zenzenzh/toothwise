import { createContext, useContext, useEffect, useState } from 'react';
import { authAPI } from '../api';
import { readAuthJSON, removeAuthItem, setAuthItem } from '../utils/authStorage';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [dentist, setDentist] = useState(() => readAuthJSON('tw_dentist'));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const clearStaffSession = () => setDentist(null);
    window.addEventListener('tw:patient-session-started', clearStaffSession);
    const onStorage = (event) => { if (event.key === 'tw_patient_token') clearStaffSession(); };
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('tw:patient-session-started', clearStaffSession); window.removeEventListener('storage', onStorage); };
  }, []);

  // rememberMe keeps this device signed in after the browser closes.
  async function login(email, password, rememberMe = false) {
    setLoading(true);
    try {
      const { data } = await authAPI.login({ email, password, remember_me: rememberMe });
      // A browser can only have one active workspace at a time. Clear the
      // patient session before exposing the staff workspace, including the
      // in-memory patient state through the cross-context event.
      removeAuthItem('tw_patient_token');
      removeAuthItem('tw_patient');
      window.dispatchEvent(new Event('tw:staff-session-started'));
      setAuthItem('tw_token', data.access_token, rememberMe);
      setAuthItem('tw_dentist', JSON.stringify(data.dentist), rememberMe);
      setDentist(data.dentist);
      return data;
    } finally { setLoading(false); }
  }

  function logout() {
    removeAuthItem('tw_token');
    removeAuthItem('tw_dentist');
    setDentist(null);
    window.dispatchEvent(new Event('tw:staff-session-ended'));
  }

  return <AuthContext.Provider value={{ dentist, login, logout, loading }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
