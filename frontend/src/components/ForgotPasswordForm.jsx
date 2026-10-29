import { useState } from 'react';
import toast from 'react-hot-toast';
import PasswordField from './PasswordField';
import { validateEmail, validatePassword, validatePHMobile, LIMITS } from '../utils/validation';

/**
 * Email-free password reset. The user proves who they are with details
 * already on their account, then sets a new password right here.
 *
 * kind="patient": email + birthdate + mobile number
 * kind="staff":   email + PRC license number
 */
export default function ForgotPasswordForm({ kind, submit, onDone }) {
  const isPatient = kind === 'patient';
  const [form, setForm] = useState({ email: '', birthdate: '', contact_number: '', license_no: '', new_password: '', confirm_password: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [busy, setBusy] = useState(false);

  function set(k, v) {
    setForm(f => ({ ...f, [k]: v }));
    if (errors[k]) setErrors(e => ({ ...e, [k]: undefined }));
    if (formError) setFormError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const emailCheck = validateEmail(form.email);
    const pwCheck = validatePassword(form.new_password);
    const phoneCheck = isPatient ? validatePHMobile(form.contact_number, { required: true }) : null;

    const next = {};
    if (!emailCheck.valid) next.email = emailCheck.message;
    if (isPatient) {
      if (!form.birthdate) next.birthdate = 'Birthdate is required.';
      if (!phoneCheck.valid) next.contact_number = phoneCheck.message;
    } else if (!form.license_no.trim()) {
      next.license_no = 'License number is required.';
    }
    if (!pwCheck.valid) next.new_password = pwCheck.message;
    if (form.new_password !== form.confirm_password) next.confirm_password = 'Passwords do not match.';
    if (Object.keys(next).length) { setErrors(next); return; }

    setBusy(true);
    try {
      const body = isPatient
        ? { email: emailCheck.value, birthdate: form.birthdate, contact_number: phoneCheck.value, new_password: form.new_password }
        : { email: emailCheck.value, license_no: form.license_no.trim(), new_password: form.new_password };
      await submit(body);
      toast.success('Password changed. You can now sign in.');
      onDone();
    } catch (err) {
      setFormError(err.friendlyMessage || 'Could not reset your password.');
    } finally {
      setBusy(false);
    }
  }

  const field = (id, key, label, props = {}) => (
    <div className="auth6-field">
      <label htmlFor={id} className="auth6-label">{label}</label>
      <input
        id={id} className="auth6-input" value={form[key]}
        onChange={e => set(key, e.target.value)}
        aria-invalid={!!errors[key]}
        aria-describedby={errors[key] ? `${id}-error` : undefined}
        required {...props}
      />
      {errors[key] && <p id={`${id}-error`} className="auth6-error" role="alert">{errors[key]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="auth6-form" noValidate>
      {formError && <div className="auth6-alert" role="alert">{formError}</div>}
      {field(`${kind}-fp-email`, 'email', 'Email address', { type: 'email', maxLength: LIMITS.EMAIL_MAX, autoComplete: 'username' })}
      {isPatient ? (
        <>
          {field('patient-fp-birthdate', 'birthdate', 'Birthdate', { type: 'date', autoComplete: 'bday' })}
          {field('patient-fp-phone', 'contact_number', 'Mobile number on your account', { type: 'tel', inputMode: 'numeric', placeholder: '09XXXXXXXXX', maxLength: LIMITS.PHONE_MAX, autoComplete: 'tel' })}
        </>
      ) : (
        field('staff-fp-license', 'license_no', 'PRC license number', { maxLength: 60, autoComplete: 'off' })
      )}
      <PasswordField
        value={form.new_password}
        onChange={v => set('new_password', v)}
        label="New Password"
        showRequirements
        error={errors.new_password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName="auth6-label"
        fieldClassName="auth6-field"
      />
      <PasswordField
        value={form.confirm_password}
        onChange={v => set('confirm_password', v)}
        label="Confirm New Password"
        error={errors.confirm_password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName="auth6-label"
        fieldClassName="auth6-field"
      />
      <button type="submit" className="auth6-submit" disabled={busy} aria-busy={busy}>
        {busy ? 'Changing password…' : 'Change Password'}
      </button>
    </form>
  );
}
