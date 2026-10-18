import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import LogoMark from './LogoMark';

// Shared shell for both auth surfaces (staff /login and the patient portal's
// sign-in/sign-up card): one centered white card on a flat cream page.
export default function AuthLayout({ children }) {
  return (
    <div className="auth6">
      <Link to="/" className="auth6-home"><ArrowLeft size={16} aria-hidden="true" /> CodiSmile Dental Clinic</Link>
      <main className="auth6-card">
        <div className="auth6-logo"><LogoMark size={56} alt="CodiSmile Dental Clinic" /></div>
        {children}
      </main>
    </div>
  );
}
