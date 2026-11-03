import { useEffect, useRef, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import LogoMark from './LogoMark';

// Data privacy consent required before anyone uses the system.
// Consent is asked once per browser session (closing the browser asks
// again), so each person using a shared clinic computer sees the notice.
// Bump the version when the notice text changes to ask everyone again.
const CONSENT_KEY = 'tw_privacy_consent_v1';

export const PRIVACY_NOTICE = [
  ['Why we collect your data', 'ToothWise collects and processes personal and health information to provide AI-assisted dental screening, keep patient records, and support CodiSmile Dental Clinic services.'],
  ['What we collect', 'Name, birthdate, sex, contact number, address, email, account details, dental screening images, screening results, clinical notes, and records of activity in the system.'],
  ['How it is protected', 'Only authorized clinic staff can see records, based on their role. Data is used only for clinic purposes, is never sold, and is not shared with outside parties except when required by law.'],
  ['AI results', 'AI screening results only assist the dentist. They are not a final diagnosis and do not replace a professional dental examination.'],
  ['Your rights', 'Under the Data Privacy Act of 2012 (Republic Act No. 10173), you have the right to be informed, to access, correct, object to, and request deletion of your data, and to file a complaint with the National Privacy Commission. Contact the clinic to exercise these rights.'],
];

function hasConsent() {
  try { return sessionStorage.getItem(CONSENT_KEY) !== null; } catch { return false; }
}

function saveConsent() {
  try { sessionStorage.setItem(CONSENT_KEY, new Date().toISOString()); } catch { /* storage blocked: consent holds for this page only */ }
}

export default function DataPrivacyGate({ children }) {
  const { pathname } = useLocation();
  const [accepted, setAccepted] = useState(hasConsent);
  const [ticked, setTicked] = useState(false);
  const boxRef = useRef(null);

  // The full privacy policy stays readable before agreeing.
  const blocked = !accepted && pathname !== '/privacy';

  useEffect(() => {
    if (!blocked) return undefined;
    boxRef.current?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [blocked]);

  function agree() {
    if (!ticked) return;
    saveConsent();
    setAccepted(true);
  }

  return (
    <>
      <div aria-hidden={blocked || undefined} inert={blocked ? '' : undefined}>{children}</div>
      {blocked && (
        <div className="dp-backdrop">
          <div
            className="dp-dialog" role="dialog" aria-modal="true"
            aria-labelledby="dp-title" aria-describedby="dp-lead"
            tabIndex={-1} ref={boxRef}
          >
            <div className="dp-head">
              <LogoMark size={40} alt="" />
              <div>
                <h2 id="dp-title"><ShieldCheck size={20} aria-hidden="true" /> Data Privacy Notice</h2>
                <p id="dp-lead">Please read and agree before using ToothWise.</p>
              </div>
            </div>
            <div className="dp-body">
              {PRIVACY_NOTICE.map(([title, text]) => (
                <section key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </section>
              ))}
              <p className="dp-more">
                <Link to="/privacy">Read the full Privacy Policy</Link>
              </p>
            </div>
            <div className="dp-foot">
              <label className="dp-check">
                <input type="checkbox" checked={ticked} onChange={e => setTicked(e.target.checked)} />
                <span>I have read and understood this Data Privacy Notice and I agree to the collection and processing of my personal information by ToothWise and CodiSmile Dental Clinic, in line with the Data Privacy Act of 2012.</span>
              </label>
              <button type="button" className="tw-btn tw-btn--primary dp-continue" disabled={!ticked} onClick={agree}>
                I Agree &amp; Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
