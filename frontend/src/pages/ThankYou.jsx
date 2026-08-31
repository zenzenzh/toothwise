import { Link } from 'react-router-dom';
import { CheckCircle2, ArrowRight } from 'lucide-react';
import SEO from '../components/SEO';
import LogoMark from '../components/LogoMark';

export default function ThankYou() {
  return (
    <div className="tw-public-page">
      <SEO title="Thank You | ToothWise" description="Thank you for contacting CodiSmile Dental Clinic through ToothWise." noIndex />
      <main className="thank-you">
        <div className="thank-you-card">
          <div className="thank-you-logo"><LogoMark size={64} alt="CodiSmile Dental Clinic" /></div>
          <CheckCircle2 size={52} className="thank-you-check" />
          <p className="public-kicker">Request received</p>
          <h1>Thank you.</h1>
          <p>Your request has been received. The clinic can review it during its normal operating workflow.</p>
          <Link to="/" className="public-button">Return to ToothWise <ArrowRight size={17} /></Link>
        </div>
      </main>
    </div>
  );
}
