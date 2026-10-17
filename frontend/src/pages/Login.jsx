import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PasswordField from '../components/PasswordField';
import AuthLayout from '../components/AuthLayout';
import { validateEmail, LIMITS } from '../utils/validation';
import SEO from '../components/SEO';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const emailRef = useRef(null);
  const { login, loading } = useAuth();
  const busy = loading || submitting;

  useEffect(() => { emailRef.current?.focus(); }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const form = e.currentTarget;
    const emailCheck = validateEmail(email);
    if (!emailCheck.valid) { setErrors({ email: emailCheck.message }); emailRef.current?.focus(); return; }
    if (!password) {
      setErrors({ password: 'Password is required.' });
      form.querySelector('input[autocomplete="current-password"]')?.focus();
      return;
    }
    setErrors({});
    setFormError(null);
    setSubmitting(true);
    try {
      await login(emailCheck.value, password);
      window.location.replace('/dashboard');
    } catch (err) {
      // Shown inline rather than as a toast so the reason stays visible
      // while the user corrects their details.
      const status = err.response?.status;
      const message = status === 429
        ? (err.friendlyMessage || 'Too many attempts. Please wait a moment and try again.')
        : status === 400 || status === 422
          ? (err.friendlyMessage || 'The server rejected the login request.')
          : status === 401
            ? 'Invalid email or password.'
            : (err.friendlyMessage || 'Unable to sign in. Please check that the ToothWise backend is running.');
      setFormError(message);
      if (status === 401) form.querySelector('input[autocomplete="current-password"]')?.select();
    } finally { setSubmitting(false); }
  }

  return (
    <>
      <SEO title="Staff Login | ToothWise" description="Secure CodiSmile Dental Clinic staff sign-in for the ToothWise clinic workspace." noIndex />
      <AuthLayout>
        <div className="auth6-head">
          <h1>Welcome back</h1>
          <p>Sign in to manage patients, screening results, and clinical records.</p>
        </div>

        <form onSubmit={handleSubmit} className="auth6-form" noValidate>
          {formError && <div className="auth6-alert" role="alert">{formError}</div>}
          <div className="auth6-field">
            <label htmlFor="login-email" className="auth6-label">Email address</label>
            <input
              id="login-email" ref={emailRef} className="auth6-input" type="email" value={email}
              onChange={e => { setEmail(e.target.value); if (errors.email) setErrors({}); if (formError) setFormError(null); }}
              placeholder="staff@codismile.com" maxLength={LIMITS.EMAIL_MAX} autoComplete="username" required
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? 'login-email-error' : undefined}
            />
            {errors.email && <p id="login-email-error" className="auth6-error" role="alert">{errors.email}</p>}
          </div>
          <PasswordField
            value={password}
            onChange={v => { setPassword(v); if (errors.password) setErrors({}); if (formError) setFormError(null); }}
            autoComplete="current-password"
            error={errors.password}
            inputClassName="auth6-input auth6-input-password"
            labelClassName="auth6-label"
            fieldClassName="auth6-field"
          />
          <button type="submit" className="auth6-submit" disabled={busy} aria-busy={busy}>
            {busy ? <span className="auth6-spinner" aria-hidden="true" /> : null}
            {busy ? 'Signing in…' : 'Sign in to workspace'}
          </button>
        </form>

        <div className="auth6-note">
          Authorized CodiSmile staff only. Patient access is available from the public clinic portal.
          <div className="auth6-note-link"><Link to="/patient-portal">Go to Patient Portal →</Link></div>
        </div>
      </AuthLayout>
    </>
  );
}
