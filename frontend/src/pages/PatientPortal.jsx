import { usePatientAuth } from '../context/PatientAuthContext';
import SEO from '../components/SEO';
import ChatWidget from '../components/ChatWidget';
import AuthCard from './portal/AuthForms';
import PortalHome from './portal/PortalHome';

export default function PatientPortal() {
  const { patient, logout } = usePatientAuth();

  function handleLogout() {
    logout();
    window.location.replace('/patient-portal');
  }

  return (
    <>
      <SEO title="Patient Portal | ToothWise" description="Secure CodiSmile patient portal for account access, AI-assisted dental screening results, and dental records." noIndex />
      {patient ? (
        <div className="pp2-root">
          <PortalHome patient={patient} onLogout={handleLogout} />
        </div>
      ) : (
        <AuthCard />
      )}
      <ChatWidget patient={patient} />
    </>
  );
}
