import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import SEO from '../components/SEO';

export default function PrivacyPolicy() {
  return (
    <div className="tw-public-page">
      <SEO title="Privacy Policy | ToothWise" description="Learn how ToothWise handles patient account, screening, and clinical information." />
      <header className="public-nav">
        <Link to="/" className="public-brand" aria-label="ToothWise home">
          <span className="public-brand-mark"><ShieldCheck size={22} /></span>
          <span><strong>ToothWise</strong><small>CodiSmile Dental Clinic</small></span>
        </Link>
        <Link to="/" className="public-nav-link"><ArrowLeft size={16} /> Home</Link>
      </header>
      <main className="legal-page">
        <p className="public-kicker">Privacy</p>
        <h1>Privacy Policy</h1>
        <p className="legal-lead">ToothWise is designed to support dental screening and clinic workflows. Patient information should be collected, accessed, and retained only for legitimate clinic purposes and according to CodiSmile's applicable privacy policies and legal obligations.</p>
        <section className="legal-card">
          <h2>Information we may process</h2>
          <p>Depending on the workflow, this can include account details, birthdate and age, dental screening images, screening results, clinical notes, and audit information.</p>
          <h2>Access and security</h2>
          <p>Access is restricted by authentication and user role. Sensitive information should not be shared outside authorized clinic workflows. The system also uses server-side validation and access controls to protect records.</p>
          <h2>AI-assisted screening</h2>
          <p>AI output is intended to assist screening workflows. It should not be presented as a definitive diagnosis or as a substitute for professional dental evaluation.</p>
          <h2>Your questions</h2>
          <p>For questions about how your information is collected, used, corrected, retained, or deleted, contact the clinic through its official privacy/contact channel.</p>
        </section>
      </main>
    </div>
  );
}
