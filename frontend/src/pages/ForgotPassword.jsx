import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import SEO from '../components/SEO';
import { authAPI, patientAuthAPI } from '../api';
import { validateEmail, LIMITS } from '../utils/validation';

// One page for both account types: ?type=staff (default) or ?type=patient.
export function accountTypeFrom(params) {
  return params.get('type') === 'patient' ? 'patient' : 'staff';
}

export function loginPathFor(type) {
  return type === 'patient' ? '/patient-portal' : '/login';
}

export default function ForgotPassword() {
  const [params] = useSearchParams();
  const type = accountTypeFrom(params);
  const [email, setEmail] = useState('');
  const [error, setError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const emailRef = useRef(null);

  useEffect(() => { emailRef.current?.focus(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const check = validateEmail(email);
    if (!check.valid) { setError(check.message); emailRef.current?.focus(); return; }
    setError(null);
    setFormError(null);
    setSubmitting(true);
    try {
      const api = type === 'patient' ? patientAuthAPI : authAPI;
      const { data } = await api.forgotPassword(check.value);
      setResult(data);
    } catch (err) {
      setFormError(err.friendlyMessage || 'Could not send the reset link. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <SEO title="Forgot Password | ToothWise" description="Reset your ToothWise account password." noIndex />
      <AuthLayout>
        <div className="auth6-head">
          <h1>Forgot your password?</h1>
          <p>
            Enter the email you use for your {type === 'patient' ? 'patient portal' : 'staff'} account.
            We'll send you a link to choose a new password.
          </p>
        </div>

        {result ? (
          <div className="auth6-form">
            <div className="auth6-success" role="status">{result.message}</div>
            {result.dev_reset_url && (
              <div className="auth6-devlink">
                Email isn't set up on this server, so here is the reset link for testing:{' '}
                <a href={result.dev_reset_url}>Open reset link</a>
              </div>
            )}
            <Link to={loginPathFor(type)} className="auth6-submit" style={{ textDecoration: 'none' }}>Back to sign in</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth6-form" noValidate>
            {formError && <div className="auth6-alert" role="alert">{formError}</div>}
            <div className="auth6-field">
              <label htmlFor="forgot-email" className="auth6-label">Email address</label>
              <input
                id="forgot-email" ref={emailRef} className="auth6-input" type="email" value={email}
                onChange={e => { setEmail(e.target.value); if (error) setError(null); if (formError) setFormError(null); }}
                maxLength={LIMITS.EMAIL_MAX} autoComplete="email" required
                aria-invalid={!!error} aria-describedby={error ? 'forgot-email-error' : undefined}
              />
              {error && <p id="forgot-email-error" className="auth6-error" role="alert">{error}</p>}
            </div>
            <button type="submit" className="auth6-submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? <span className="auth6-spinner" aria-hidden="true" /> : null}
              {submitting ? 'Sending…' : 'Send reset link'}
            </button>
          </form>
        )}

        <div className="auth6-note">
          Remembered it?
          <div className="auth6-note-link"><Link to={loginPathFor(type)}>Back to sign in →</Link></div>
        </div>
      </AuthLayout>
    </>
  );
}
