import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import SEO from '../components/SEO';
import LogoMark from '../components/LogoMark';

const SECTIONS = [
  ['Information we may process', 'Depending on the workflow, this can include account details, birthdate and age, dental screening images, screening results, clinical notes, and audit information.'],
  ['Access and security', 'Access is restricted by authentication and user role. Sensitive information should not be shared outside authorized clinic workflows. The system also uses server-side validation and access controls to protect records.'],
  ['AI-assisted screening', 'AI output is intended to assist screening workflows. It should not be presented as a definitive diagnosis or as a substitute for professional dental evaluation.'],
  ['Your questions', 'For questions about how your information is collected, used, corrected, retained, or deleted, contact the clinic through its official privacy/contact channel.'],
];

export default function PrivacyPolicy() {
  return (
    <div className="tw-public-page">
      <SEO title="Privacy Policy | ToothWise" description="Learn how ToothWise handles patient account, screening, and clinical information." />
      <header className="public-nav">
        <Link to="/" className="public-brand" aria-label="ToothWise home">
          <span className="public-brand-mark"><LogoMark size={42} alt="" /></span>
          <span><strong>ToothWise</strong><small>CodiSmile Dental Clinic</small></span>
        </Link>
        <Link to="/" className="public-nav-link"><ArrowLeft size={16} /> Home</Link>
      </header>
      <main className="legal-page">
        <div className="legal-intro">
          <h1>Privacy Policy</h1>
          <p className="legal-lead">ToothWise supports dental screening and clinic workflows. Patient information is collected, accessed, and retained only for legitimate clinic purposes, in line with CodiSmile’s privacy policies and legal obligations.</p>
        </div>
        <section className="legal-card" aria-label="Policy details">
          {SECTIONS.map(([title, text]) => (
            <div key={title}>
              <h2>{title}</h2>
              <p>{text}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
