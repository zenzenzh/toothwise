import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PasswordField from '../components/PasswordField';
import AuthLayout from '../components/AuthLayout';
import { validateEmail, LIMITS } from '../utils/validation';
import toast from 'react-hot-toast';
import SEO from '../components/SEO';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const { login, loading } = useAuth();
  const busy = loading || submitting;

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const emailCheck = validateEmail(email);
    if (!emailCheck.valid) return setErrors({ email: emailCheck.message });
    if (!password) return setErrors({ password: 'Password is required.' });
    setErrors({});
    setSubmitting(true);
    try {
      await login(emailCheck.value, password);
      window.location.replace('/dashboard');
    } catch (err) {
      if (err.response?.status === 429) {
        toast.error(err.friendlyMessage || 'Too many attempts. Please wait a moment and try again.');
      } else if (err.response?.status === 400 || err.response?.status === 422) {
        toast.error(err.friendlyMessage || 'The server rejected the login request.');
      } else if (err.response?.status === 401) {
        toast.error('Invalid email or password.');
      } else {
        toast.error(err.friendlyMessage || 'Unable to sign in. Please check that the ToothWise backend is running.');
      }
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
          <div className="auth6-field">
            <label htmlFor="login-email" className="auth6-label">Email address</label>
            <input
              id="login-email" className="auth6-input" type="email" value={email}
              onChange={e => { setEmail(e.target.value); if (errors.email) setErrors({}); }}
              placeholder="staff@codismile.com" maxLength={LIMITS.EMAIL_MAX} autoComplete="username" required
              aria-invalid={!!errors.email}
            />
            {errors.email && <p className="auth6-error" role="alert">{errors.email}</p>}
          </div>
          <PasswordField
            value={password}
            onChange={v => { setPassword(v); if (errors.password) setErrors({}); }}
            autoComplete="current-password"
            error={errors.password}
            inputClassName="auth6-input auth6-input-password"
            labelClassName="auth6-label"
            fieldClassName="auth6-field"
          />
          <button className="auth6-submit" disabled={busy}>
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
