import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePatientAuth } from '../../context/PatientAuthContext';
import PasswordField from '../../components/PasswordField';
import AuthLayout from '../../components/AuthLayout';
import AuthOptionsRow from '../../components/AuthOptionsRow';
import { validateEmail, validatePHMobile, validatePassword, validateRequiredText, validateOptionalText, LIMITS } from '../../utils/validation';
import toast from 'react-hot-toast';

function calculateAge(birthdate) {
  if (!birthdate) return '';
  const birth = new Date(`${birthdate}T00:00:00`);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const month = today.getMonth() - birth.getMonth();
  if (month < 0 || (month === 0 && today.getDate() < birth.getDate())) age--;
  return age >= 0 ? age : '';
}

function getLocalDateString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60000);
  return local.toISOString().slice(0, 10);
}

// Focus the first field (in form order) that failed validation.
function focusFirstError(form, errors) {
  const first = [...form.querySelectorAll('input, select, textarea')]
    .find(el => el.dataset.field && errors[el.dataset.field]);
  first?.focus();
}

function TextField({ id, field, label, error, hint, className = 'auth6-field', ...inputProps }) {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="auth6-label">{label}</label>
      <input
        id={id}
        data-field={field}
        className="auth6-input"
        aria-invalid={!!error}
        aria-describedby={describedBy}
        {...inputProps}
      />
      {error && <p id={errorId} className="auth6-error" role="alert">{error}</p>}
      {hint && <p id={hintId} className="auth6-hint">{hint}</p>}
    </div>
  );
}

export default function AuthCard() {
  const [mode, setMode] = useState('login');
  const isLogin = mode === 'login';

  return (
    <AuthLayout>
      <div className="auth6-head">
        <h1>{isLogin ? 'Welcome back' : 'Create your account'}</h1>
        <p>
          {isLogin
            ? 'Sign in to view your screenings and dental records.'
            : 'Register to view your AI-assisted screening results and dental records.'}
        </p>
      </div>

      <div className="auth6-tabs" role="tablist" aria-label="Account mode">
        <span
          className="auth6-tab-pill"
          aria-hidden="true"
          style={{ transform: isLogin ? 'translateX(0)' : 'translateX(100%)' }}
        />
        <button type="button" role="tab" id="auth-tab-login" aria-controls="auth-panel" aria-selected={isLogin} className={isLogin ? 'is-active' : ''} onClick={() => setMode('login')}>Sign in</button>
        <button type="button" role="tab" id="auth-tab-register" aria-controls="auth-panel" aria-selected={!isLogin} className={!isLogin ? 'is-active' : ''} onClick={() => setMode('register')}>Sign up</button>
      </div>

      <div id="auth-panel" role="tabpanel" aria-labelledby={isLogin ? 'auth-tab-login' : 'auth-tab-register'}>
        {isLogin ? <LoginForm /> : <RegisterForm />}
      </div>

      <div className="auth6-note">
        {isLogin ? "Don't have an account? " : 'Already registered? '}
        <button type="button" className="auth6-note-toggle" onClick={() => setMode(isLogin ? 'register' : 'login')}>
          {isLogin ? 'Sign up' : 'Sign in'}
        </button>
        <div className="auth6-note-link"><Link to="/login">Staff Login →</Link></div>
      </div>
    </AuthLayout>
  );
}

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const { login, loading } = usePatientAuth();
  const busy = loading || submitting;

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const form = e.currentTarget;

    const emailCheck = validateEmail(email);
    const nextErrors = {};
    if (!emailCheck.valid) nextErrors.email = emailCheck.message;
    else if (!password) nextErrors.password = 'Password is required.';
    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      if (nextErrors.email) form.querySelector('#portal-login-email')?.focus();
      else form.querySelector('input[type="password"], input[autocomplete="current-password"]')?.focus();
      return;
    }

    setErrors({});
    setSubmitting(true);
    try {
      await login(emailCheck.value, password, remember);
      toast.success('Welcome back!');
    } catch (err) {
      const status = err.response?.status;
      toast.error(status === 429 ? err.friendlyMessage : 'Invalid email or password.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth6-form" noValidate>
      <TextField
        id="portal-login-email"
        field="email"
        label="Email Address"
        type="email"
        value={email}
        onChange={e => { setEmail(e.target.value); if (errors.email) setErrors({}); }}
        maxLength={LIMITS.EMAIL_MAX}
        autoComplete="username"
        required
        error={errors.email}
      />
      <PasswordField
        value={password}
        onChange={v => { setPassword(v); if (errors.password) setErrors({}); }}
        autoComplete="current-password"
        error={errors.password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName="auth6-label"
        fieldClassName="auth6-field"
      />
      <AuthOptionsRow remember={remember} onRememberChange={setRemember} forgotTo="/forgot-password?type=patient" />
      <button type="submit" className="auth6-submit" disabled={busy} aria-busy={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
    </form>
  );
}

function RegisterForm() {
  const [form, setForm] = useState({ first_name: '', middle_name: '', last_name: '', email: '', password: '', confirm_password: '', contact_number: '', birthdate: '', gender: '' });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const { register, loading } = usePatientAuth();
  const busy = loading || submitting;

  function set(k, v) {
    setForm(f => ({ ...f, [k]: v }));
    if (errors[k]) setErrors(e => ({ ...e, [k]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    const formEl = e.currentTarget;

    const firstCheck = validateRequiredText(form.first_name, 'First name');
    const lastCheck = validateRequiredText(form.last_name, 'Last name');
    const middleCheck = validateOptionalText(form.middle_name, 'Middle name', LIMITS.NAME_MAX);
    const emailCheck = validateEmail(form.email);
    const phoneCheck = validatePHMobile(form.contact_number, { required: true });
    const passwordCheck = validatePassword(form.password);
    const age = calculateAge(form.birthdate);

    const nextErrors = {};
    if (!firstCheck.valid) nextErrors.first_name = firstCheck.message;
    if (!lastCheck.valid) nextErrors.last_name = lastCheck.message;
    if (!middleCheck.valid) nextErrors.middle_name = middleCheck.message;
    if (!emailCheck.valid) nextErrors.email = emailCheck.message;
    if (!phoneCheck.valid) nextErrors.contact_number = phoneCheck.message;
    if (!form.birthdate) nextErrors.birthdate = 'Birthdate is required.';
    else if (new Date(`${form.birthdate}T00:00:00`) > new Date()) nextErrors.birthdate = 'Birthdate cannot be in the future.';
    else if (age === '') nextErrors.birthdate = 'Enter a valid birthdate.';
    if (!passwordCheck.valid) nextErrors.password = passwordCheck.message;
    if (form.password !== form.confirm_password) nextErrors.confirm_password = 'Passwords do not match.';

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      focusFirstError(formEl, nextErrors);
      return;
    }

    setErrors({});
    setSubmitting(true);
    try {
      await register({
        first_name: firstCheck.value,
        middle_name: middleCheck.value || null,
        last_name: lastCheck.value,
        email: emailCheck.value,
        password: form.password,
        contact_number: phoneCheck.value,
        birthdate: form.birthdate,
        gender: form.gender || null,
      });
      toast.success('Account created!');
    } catch (err) {
      toast.error(err.friendlyMessage || 'Could not create account.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth6-form" noValidate>
      <div className="auth6-grid auth6-grid-2">
        <TextField id="reg-first-name" field="first_name" label="First Name" value={form.first_name} onChange={e => set('first_name', e.target.value)} maxLength={LIMITS.NAME_MAX} autoComplete="given-name" required error={errors.first_name} />
        <TextField id="reg-middle-name" field="middle_name" label="Middle Name / Initial" value={form.middle_name} onChange={e => set('middle_name', e.target.value)} maxLength={LIMITS.NAME_MAX} autoComplete="additional-name" error={errors.middle_name} />
        <TextField id="reg-last-name" field="last_name" label="Last Name" className="auth6-field auth6-span-2" value={form.last_name} onChange={e => set('last_name', e.target.value)} maxLength={LIMITS.NAME_MAX} autoComplete="family-name" required error={errors.last_name} />
      </div>
      <TextField id="reg-email" field="email" label="Email Address" type="email" value={form.email} onChange={e => set('email', e.target.value)} maxLength={LIMITS.EMAIL_MAX} autoComplete="email" required error={errors.email} />
      <TextField
        id="reg-phone"
        field="contact_number"
        label="Mobile Number"
        type="tel"
        inputMode="numeric"
        placeholder="09XXXXXXXXX"
        value={form.contact_number}
        onChange={e => set('contact_number', e.target.value)}
        maxLength={LIMITS.PHONE_MAX}
        autoComplete="tel"
        required
        error={errors.contact_number}
        hint="Used by the clinic to reach you about your records."
      />
      <div className="auth6-grid auth6-grid-2">
        <div className="auth6-field">
          <label htmlFor="reg-gender" className="auth6-label">Gender</label>
          <select id="reg-gender" className="auth6-input" value={form.gender} onChange={e => set('gender', e.target.value)} autoComplete="sex">
            <option value="">Select</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <TextField id="reg-birthdate" field="birthdate" label="Birthdate" type="date" max={getLocalDateString()} value={form.birthdate} onChange={e => set('birthdate', e.target.value)} autoComplete="bday" required error={errors.birthdate} />
      </div>
      <PasswordField
        value={form.password}
        onChange={v => set('password', v)}
        showRequirements
        error={errors.password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName="auth6-label"
        fieldClassName="auth6-field"
      />
      <PasswordField
        value={form.confirm_password}
        onChange={v => set('confirm_password', v)}
        label="Confirm Password"
        error={errors.confirm_password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName="auth6-label"
        fieldClassName="auth6-field"
      />
      <button type="submit" className="auth6-submit" disabled={busy} aria-busy={busy}>{busy ? 'Creating account…' : 'Create Account'}</button>
    </form>
  );
}
