import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import PasswordField from '../components/PasswordField';
import SEO from '../components/SEO';
import { authAPI, patientAuthAPI } from '../api';
import { validatePassword } from '../utils/validation';
import { accountTypeFrom, loginPathFor } from './ForgotPassword';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const type = accountTypeFrom(params);
  const token = params.get('token') || '';
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  function set(key, value) {
    setForm(f => ({ ...f, [key]: value }));
    if (errors[key]) setErrors(e => ({ ...e, [key]: undefined }));
    if (formError) setFormError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (submitting) return;
    const check = validatePassword(form.password);
    const next = {};
    if (!check.valid) next.password = check.message;
    else if (form.password !== form.confirm) next.confirm = 'Passwords do not match.';
    if (Object.keys(next).length) { setErrors(next); return; }
    setErrors({});
    setSubmitting(true);
    try {
      const api = type === 'patient' ? patientAuthAPI : authAPI;
      await api.resetPassword(token, form.password);
      setDone(true);
    } catch (err) {
      setFormError(err.friendlyMessage || 'Could not reset your password. Please request a new link.');
    } finally {
      setSubmitting(false);
    }
  }

  const forgotLink = `/forgot-password?type=${type}`;

  return (
    <>
      <SEO title="Reset Password | ToothWise" description="Choose a new ToothWise account password." noIndex />
      <AuthLayout>
        <div className="auth6-head">
          <h1>{done ? 'Password updated' : 'Choose a new password'}</h1>
          <p>{done ? 'You can now sign in with your new password.' : 'Pick a password you haven’t used here before.'}</p>
        </div>

        {done ? (
          <div className="auth6-form">
            <div className="auth6-success" role="status">Your password has been reset.</div>
            <Link to={loginPathFor(type)} className="auth6-submit" style={{ textDecoration: 'none' }}>Go to sign in</Link>
          </div>
        ) : !token ? (
          <div className="auth6-form">
            <div className="auth6-alert" role="alert">This reset link is incomplete. Please request a new one.</div>
            <Link to={forgotLink} className="auth6-submit" style={{ textDecoration: 'none' }}>Request a new link</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth6-form" noValidate>
            {formError && (
              <div className="auth6-alert" role="alert">
                {formError} <Link to={forgotLink}>Request a new link</Link>
              </div>
            )}
            <PasswordField
              value={form.password}
              onChange={v => set('password', v)}
              label="New password"
              showRequirements
              error={errors.password}
              inputClassName="auth6-input auth6-input-password"
              labelClassName="auth6-label"
              fieldClassName="auth6-field"
            />
            <PasswordField
              value={form.confirm}
              onChange={v => set('confirm', v)}
              label="Confirm new password"
              error={errors.confirm}
              inputClassName="auth6-input auth6-input-password"
              labelClassName="auth6-label"
              fieldClassName="auth6-field"
            />
            <button type="submit" className="auth6-submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? <span className="auth6-spinner" aria-hidden="true" /> : null}
              {submitting ? 'Saving…' : 'Reset password'}
            </button>
          </form>
        )}
      </AuthLayout>
    </>
  );
}
