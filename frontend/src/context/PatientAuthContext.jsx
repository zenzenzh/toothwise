import { createContext, useContext, useEffect, useState } from 'react';
import { patientAuthAPI } from '../api';
import { readAuthJSON, removeAuthItem, setAuthItem } from '../utils/authStorage';

const PatientAuthContext = createContext(null);

export function PatientAuthProvider({ children }) {
  const [patient, setPatient] = useState(() => readAuthJSON('tw_patient'));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const clearPatientSession = () => setPatient(null);
    window.addEventListener('tw:staff-session-started', clearPatientSession);
    const onStorage = (event) => { if (event.key === 'tw_token') clearPatientSession(); };
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('tw:staff-session-started', clearPatientSession); window.removeEventListener('storage', onStorage); };
  }, []);

  // A browser can only have one active workspace at a time. Clear the staff
  // session before exposing the patient workspace, including the in-memory
  // staff state through the cross-context event.
  function startSession(data, rememberMe) {
    removeAuthItem('tw_token');
    removeAuthItem('tw_dentist');
    window.dispatchEvent(new Event('tw:patient-session-started'));
    setAuthItem('tw_patient_token', data.access_token, rememberMe);
    setAuthItem('tw_patient', JSON.stringify(data.patient), rememberMe);
    setPatient(data.patient);
  }

  // rememberMe keeps this device signed in after the browser closes.
  async function login(email, password, rememberMe = false) {
    setLoading(true);
    try {
      const { data } = await patientAuthAPI.login({ email, password, remember_me: rememberMe });
      startSession(data, rememberMe);
      return data;
    } finally { setLoading(false); }
  }

  async function register(payload) {
    setLoading(true);
    try {
      const { data } = await patientAuthAPI.register(payload);
      // Same lifetime as before this change: a new account stays signed in
      // on this device until the token expires or the patient signs out.
      startSession(data, true);
      return data;
    } finally { setLoading(false); }
  }

  function logout() {
    removeAuthItem('tw_patient_token');
    removeAuthItem('tw_patient');
    setPatient(null);
    window.dispatchEvent(new Event('tw:patient-session-ended'));
  }

  return (
    <PatientAuthContext.Provider value={{ patient, login, register, logout, loading }}>
      {children}
    </PatientAuthContext.Provider>
  );
}

export const usePatientAuth = () => useContext(PatientAuthContext);
