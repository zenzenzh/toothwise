import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { PatientAuthProvider } from './context/PatientAuthContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import RouteFallback from './components/RouteFallback';

import { can } from './utils/permissions';

// Public entry pages stay in the main bundle; everything behind them
// (staff workspace, charts, portal, static pages) loads on demand, so the
// landing page doesn't ship recharts and every staff screen up front.
const PatientPortal = lazy(() => import('./pages/PatientPortal'));
const Layout = lazy(() => import('./components/Layout'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Patients = lazy(() => import('./pages/Patients'));
const PatientDetail = lazy(() => import('./pages/PatientDetail'));
const Screening = lazy(() => import('./pages/Screening'));
const ScreeningDetail = lazy(() => import('./pages/ScreeningDetail'));
const Dentists = lazy(() => import('./pages/Dentists'));
const AuditLog = lazy(() => import('./pages/AuditLog'));
const NotFound = lazy(() => import('./pages/NotFound'));
const PrivacyPolicy = lazy(() => import('./pages/PrivacyPolicy'));
const ThankYou = lazy(() => import('./pages/ThankYou'));

function Protected({ children }) {
  const { dentist } = useAuth();
  return dentist ? children : <Navigate to="/login" replace />;
}

// Dentist/administrator only: staff management and the audit trail.
function DentistOnly({ children }) {
  const { dentist } = useAuth();
  return can(dentist?.role, 'manageStaff') ? children : <Navigate to="/dashboard" replace />;
}

// Clinical work (screenings) is open to the dentist and the assistant;
// receptionists are kept out of clinical data.
function ClinicalOnly({ children }) {
  const { dentist } = useAuth();
  return can(dentist?.role, 'clinical') ? children : <Navigate to="/dashboard" replace />;
}

function RootRoute() {
  const { dentist } = useAuth();
  return dentist ? <Navigate to="/dashboard" replace /> : <Landing />;
}

// Logging out (and any 401) uses a real window navigation rather than
// React Router, so the browser treats it as a real page load - which makes
// the page the user was just on (e.g. the dashboard) eligible for the
// browser's back-forward cache (bfcache). Pressing the physical Back
// button can then restore that FROZEN snapshot exactly as it looked while
// still logged in, without re-running any JS - including the check that
// would normally redirect an unauthenticated visitor to /login, since
// nothing actually re-executes on a bfcache restore.
//
// The fix: listen for `pageshow` and check `event.persisted`, which is
// true specifically when the page came back from bfcache rather than a
// fresh load. When that happens, force a real reload - this discards the
// stale frozen snapshot and re-runs the app from scratch, which correctly
// reads the now-cleared token from localStorage and shows the login page.
function useBfcacheGuard() {
  useEffect(() => {
    function handlePageShow(event) {
      if (event.persisted) {
        window.location.reload();
      }
    }
    window.addEventListener('pageshow', handlePageShow);
    return () => window.removeEventListener('pageshow', handlePageShow);
  }, []);
}

export default function App() {
  useBfcacheGuard();
  return (
    <AuthProvider>
      <PatientAuthProvider>
        <BrowserRouter>
          <Toaster
            position="top-right"
            toastOptions={{
              style: {
                background: '#181B23',
                color: '#F0F0F3',
                border: '1px solid #262A33',
                fontFamily: "Inter, 'Segoe UI', Arial, sans-serif",
                fontSize: '14px',
              },
              success: { iconTheme: { primary: '#BA7976', secondary: '#181B23' } },
              error: { iconTheme: { primary: '#EF4444', secondary: '#181B23' } },
            }}
          />
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<RootRoute />} />
            <Route path="/login" element={<Login />} />
            <Route path="/patient-portal" element={<PatientPortal />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/thank-you" element={<ThankYou />} />

            <Route path="/dashboard" element={<Protected><Layout /></Protected>}>
              <Route index element={<Dashboard />} />
              <Route path="patients" element={<Patients />} />
              <Route path="patients/:id" element={<PatientDetail />} />
              <Route path="patients/:id/screening" element={<ClinicalOnly><Screening /></ClinicalOnly>} />
              <Route path="screenings/:id" element={<ClinicalOnly><ScreeningDetail /></ClinicalOnly>} />
              <Route path="dentists" element={<DentistOnly><Dentists /></DentistOnly>} />
              <Route path="audit-log" element={<DentistOnly><AuditLog /></DentistOnly>} />
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
        </BrowserRouter>
      </PatientAuthProvider>
    </AuthProvider>
  );
}
