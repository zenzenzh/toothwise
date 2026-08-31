import { createContext, useContext, useEffect, useState } from 'react';
import { patientAuthAPI } from '../api';

const PatientAuthContext = createContext(null);

export function PatientAuthProvider({ children }) {
  const [patient, setPatient] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tw_patient')); } catch { return null; }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const clearPatientSession = () => setPatient(null);
    window.addEventListener('tw:staff-session-started', clearPatientSession);
    const onStorage = (event) => { if (event.key === 'tw_token') clearPatientSession(); };
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('tw:staff-session-started', clearPatientSession); window.removeEventListener('storage', onStorage); };
  }, []);

  async function login(email, password) {
    setLoading(true);
    try {
      const { data } = await patientAuthAPI.login({ email, password });
      // A browser can only have one active workspace at a time. Clear the
      // staff session before exposing the patient workspace, including the
      // in-memory staff state through the cross-context event.
      localStorage.removeItem('tw_token');
      localStorage.removeItem('tw_dentist');
      window.dispatchEvent(new Event('tw:patient-session-started'));
      localStorage.setItem('tw_patient_token', data.access_token);
      localStorage.setItem('tw_patient', JSON.stringify(data.patient));
      setPatient(data.patient);
      return data;
    } finally { setLoading(false); }
  }

  async function register(payload) {
    setLoading(true);
    try {
      const { data } = await patientAuthAPI.register(payload);
      localStorage.removeItem('tw_token');
      localStorage.removeItem('tw_dentist');
      window.dispatchEvent(new Event('tw:patient-session-started'));
      localStorage.setItem('tw_patient_token', data.access_token);
      localStorage.setItem('tw_patient', JSON.stringify(data.patient));
      setPatient(data.patient);
      return data;
    } finally { setLoading(false); }
  }

  function logout() {
    localStorage.removeItem('tw_patient_token');
    localStorage.removeItem('tw_patient');
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
