import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, SearchX } from 'lucide-react';
import SEO from '../components/SEO';
import LogoMark from '../components/LogoMark';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="tw-public-page">
      <SEO title="Page Not Found | ToothWise" description="The ToothWise page you requested could not be found." noIndex />
      <header className="public-nav">
        <Link to="/" className="public-brand" aria-label="ToothWise home">
          <span className="public-brand-mark"><LogoMark size={42} alt="" /></span>
          <span><strong>ToothWise</strong><small>CodiSmile Dental Clinic</small></span>
        </Link>
      </header>
      <main className="not-found">
        <div className="not-found-icon" aria-hidden="true"><SearchX size={44} /></div>
        <h1>That page doesn’t exist.</h1>
        <p>Error 404. It may have moved, expired, or the address may be incorrect.</p>
        <div className="not-found-actions">
          <button className="public-button" onClick={() => navigate(-1)}><ArrowLeft size={17} /> Go back</button>
          <Link className="public-button secondary" to="/"><Home size={17} /> Go home</Link>
        </div>
      </main>
    </div>
  );
}
