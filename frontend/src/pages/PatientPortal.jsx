import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircleQuestion, Microscope, TriangleAlert, ArrowLeft, ChevronRight, LogOut, Star, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { usePatientAuth } from '../context/PatientAuthContext';
import { patientScreeningsAPI } from '../api';
import { formatDatePH } from '../utils/datetime';
import PasswordField from '../components/PasswordField';
import AuthLayout from '../components/AuthLayout';
import { SkeletonBlock, SkeletonCard } from '../components/Skeleton';
import { validateEmail, validatePHMobile, validatePassword, validateRequiredText, validateOptionalText, LIMITS } from '../utils/validation';
import toast from 'react-hot-toast';
import SEO from '../components/SEO';
import ChatWidget from '../components/ChatWidget';
import LogoMark from '../components/LogoMark';

const CLASS_COLORS = {
  healthy_tooth:       '#166534',
  cavity:              '#B91C1C',
  gum_inflammation:    '#C2410C',
  plaque:              '#A16207',
  tartar:              '#92400E',
};

function BoundingBoxCanvas({ imageUrl, detections }) {
  const canvasRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);

  useEffect(() => {
    if (!imageUrl || !detections) return;
    setImgLoaded(false);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      detections.forEach(d => {
        const x = d.x1 * img.naturalWidth;
        const y = d.y1 * img.naturalHeight;
        const w = (d.x2 - d.x1) * img.naturalWidth;
        const h = (d.y2 - d.y1) * img.naturalHeight;

        const color = CLASS_COLORS[d.label] || '#B91C1C';
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(4, img.naturalWidth / 200);
        ctx.strokeRect(x, y, w, h);

        const label = `${d.label.replace(/_/g, ' ')} ${(d.confidence * 100).toFixed(0)}%`;
        const fontSize = Math.max(14, img.naturalWidth / 40);
        ctx.font = `bold ${fontSize}px Arial`;
        const textW = ctx.measureText(label).width;

        ctx.fillStyle = color;
        ctx.fillRect(x, y - fontSize - 10, textW + 10, fontSize + 10);
        ctx.fillStyle = '#FFFFFF';
        ctx.fillText(label, x + 5, y - 8);
      });
      setImgLoaded(true);
    };
    img.src = imageUrl;
  }, [imageUrl, detections]);

  return (
    <div className="pp-canvas-wrap">
      <img src={imageUrl} alt="Screening with detection annotations" style={{ width: '100%', display: imgLoaded ? 'none' : 'block' }} />
      <canvas ref={canvasRef} style={{ width: '100%', display: imgLoaded ? 'block' : 'none', height: 'auto' }} aria-label={`Screening results with ${detections?.length || 0} findings annotated`} role="img" />
      {detections?.length > 0 && (
        <ul style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', margin: -1, padding: 0, border: 0 }}>
          {detections.map((d, i) => (
            <li key={i}>{d.label.replace(/_/g, ' ')} detected with {(d.confidence * 100).toFixed(0)}% confidence</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ScreeningThumbnail({ screeningId }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    patientScreeningsAPI.imageObjectUrl(screeningId).then(u => {
      if (cancelled) { window.URL.revokeObjectURL(u); return; }
      objectUrl = u;
      setUrl(u);
    }).catch(() => setUrl(null));
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [screeningId]);

  if (!url) return <div className="pp-thumb pp-thumb--skeleton" />;
  return <img src={url} alt="Screening" className="pp-thumb" />;
}

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

export default function PatientPortal() {
  const { patient, logout } = usePatientAuth();

  function handleLogout() {
    logout();
    window.location.replace('/patient-portal');
  }
  return (
    <>
      <SEO title="Patient Portal | ToothWise" description="Secure CodiSmile patient portal for account access, AI-assisted dental screening results, and dental records." noIndex />
      {patient ? (
        <div className="pp2-root">
          <PortalHome patient={patient} onLogout={handleLogout} />
        </div>
      ) : (
        <AuthCard />
      )}
      <ChatWidget patient={patient} />
    </>
  );
}

/* ─── Auth ─────────────────────────────────────────────────────────── */

function AuthCard() {
  const [mode, setMode] = useState('login');

  return (
    <AuthLayout>
      <div className="auth6-head">
        <h1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p>
          {mode === 'login'
            ? 'Sign in to view your screenings and dental records.'
            : 'Register to view your AI-assisted screening results and dental records.'}
        </p>
      </div>

      <div className="auth6-tabs" role="tablist" aria-label="Account mode">
        <span
          className="auth6-tab-pill"
          aria-hidden="true"
          style={{ transform: mode === 'login' ? 'translateX(0)' : 'translateX(100%)' }}
        />
        <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'is-active' : ''} onClick={() => setMode('login')}>Sign in</button>
        <button type="button" role="tab" aria-selected={mode === 'register'} className={mode === 'register' ? 'is-active' : ''} onClick={() => setMode('register')}>Sign up</button>
      </div>

      {mode === 'login' ? <LoginForm /> : <RegisterForm />}

      <div className="auth6-note">
        {mode === 'login' ? "Don't have an account? " : 'Already registered? '}
        <button type="button" className="auth6-note-toggle" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Sign up' : 'Sign in'}
        </button>
        <div className="auth6-note-link"><Link to="/login">Staff Login →</Link></div>
      </div>
    </AuthLayout>
  );
}

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const { login, loading } = usePatientAuth();
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
      <div className="auth6-field">
        <label htmlFor="portal-login-email" className="auth6-label">Email Address</label>
        <input
          id="portal-login-email"
          className="auth6-input"
          type="email"
          value={email}
          onChange={e => { setEmail(e.target.value); if (errors.email) setErrors({}); }}
          maxLength={LIMITS.EMAIL_MAX}
          autoComplete="username"
          required
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? 'login-email-error' : undefined}
        />
        {errors.email && <p id="login-email-error" className="auth6-error" role="alert">{errors.email}</p>}
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
      <button className="auth6-submit" disabled={busy}>{busy ? 'Signing in...' : 'Sign In'}</button>
    </form>
  );
}

function RegisterForm() {
  const [form, setForm] = useState({ first_name: '', middle_name: '', last_name: '', email: '', password: '', confirm_password: '', contact_number: '', birthdate: '', gender: '', address: '' });
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

    const firstCheck = validateRequiredText(form.first_name, 'First name');
    const lastCheck = validateRequiredText(form.last_name, 'Last name');
    const middleCheck = validateOptionalText(form.middle_name, 'Middle name', LIMITS.NAME_MAX);
    const emailCheck = validateEmail(form.email);
    const phoneCheck = validatePHMobile(form.contact_number, { required: true });
    const passwordCheck = validatePassword(form.password);
    const addressCheck = form.address ? validateRequiredText(form.address, 'Address') : { valid: true, value: '' };
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
    if (!addressCheck.valid) nextErrors.address = addressCheck.message;
    if (form.password !== form.confirm_password) nextErrors.confirm_password = 'Passwords do not match.';

    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
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
        address: form.address ? addressCheck.value : null,
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
        <div className="auth6-field">
          <label htmlFor="reg-first-name" className="auth6-label auth6-label-row">First Name</label>
          <input
            id="reg-first-name"
            className="auth6-input"
            value={form.first_name}
            onChange={e => set('first_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="given-name"
            required
            aria-invalid={!!errors.first_name}
            aria-describedby={errors.first_name ? 'reg-first-error' : undefined}
          />
          {errors.first_name && <p id="reg-first-error" className="auth6-error" role="alert">{errors.first_name}</p>}
        </div>
        <div className="auth6-field">
          <label htmlFor="reg-middle-name" className="auth6-label auth6-label-row">Middle Name / Initial</label>
          <input
            id="reg-middle-name"
            className="auth6-input"
            value={form.middle_name}
            onChange={e => set('middle_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="additional-name"
            aria-invalid={!!errors.middle_name}
            aria-describedby={errors.middle_name ? 'reg-middle-error' : undefined}
          />
          {errors.middle_name && <p id="reg-middle-error" className="auth6-error" role="alert">{errors.middle_name}</p>}
        </div>
        <div className="auth6-field auth6-span-2">
          <label htmlFor="reg-last-name" className="auth6-label">Last Name</label>
          <input
            id="reg-last-name"
            className="auth6-input"
            value={form.last_name}
            onChange={e => set('last_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="family-name"
            required
            aria-invalid={!!errors.last_name}
            aria-describedby={errors.last_name ? 'reg-last-error' : undefined}
          />
          {errors.last_name && <p id="reg-last-error" className="auth6-error" role="alert">{errors.last_name}</p>}
        </div>
      </div>
      <div className="auth6-field">
        <label htmlFor="reg-email" className="auth6-label">Email Address</label>
        <input
          id="reg-email"
          className="auth6-input"
          type="email"
          value={form.email}
          onChange={e => set('email', e.target.value)}
          maxLength={LIMITS.EMAIL_MAX}
          autoComplete="email"
          required
          aria-invalid={!!errors.email}
          aria-describedby={errors.email ? 'reg-email-error' : undefined}
        />
        {errors.email && <p id="reg-email-error" className="auth6-error" role="alert">{errors.email}</p>}
      </div>
      <div className="auth6-field">
        <label htmlFor="reg-phone" className="auth6-label">Mobile Number</label>
        <input
          id="reg-phone"
          className="auth6-input"
          placeholder="09XXXXXXXXX"
          value={form.contact_number}
          onChange={e => set('contact_number', e.target.value)}
          maxLength={LIMITS.PHONE_MAX}
          autoComplete="tel"
          required
          aria-invalid={!!errors.contact_number}
          aria-describedby={errors.contact_number ? 'reg-phone-error' : undefined}
        />
        {errors.contact_number && <p id="reg-phone-error" className="auth6-error" role="alert">{errors.contact_number}</p>}
        <p className="auth6-hint">Used by the clinic to reach you about your records.</p>
      </div>
      <div className="auth6-grid auth6-grid-2">
        <div className="auth6-field">
          <label htmlFor="reg-gender" className="auth6-label">Gender</label>
          <select
            id="reg-gender"
            className="auth6-input"
            value={form.gender}
            onChange={e => set('gender', e.target.value)}
            autoComplete="sex"
          >
            <option value="">Select</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div className="auth6-field">
          <label htmlFor="reg-birthdate" className="auth6-label">Birthdate</label>
          <input
            id="reg-birthdate"
            className="auth6-input"
            type="date"
            max={getLocalDateString()}
            value={form.birthdate}
            onChange={e => set('birthdate', e.target.value)}
            autoComplete="bday"
            required
            aria-invalid={!!errors.birthdate}
            aria-describedby={errors.birthdate ? 'reg-birth-error' : undefined}
          />
          {errors.birthdate && <p id="reg-birth-error" className="auth6-error" role="alert">{errors.birthdate}</p>}
        </div>
      </div>
      <div className="auth6-field">
        <label htmlFor="reg-address" className="auth6-label">Address</label>
        <input
          id="reg-address"
          className="auth6-input"
          value={form.address}
          onChange={e => set('address', e.target.value)}
          maxLength={LIMITS.ADDRESS_MAX}
          autoComplete="street-address"
          aria-invalid={!!errors.address}
          aria-describedby={errors.address ? 'reg-address-error' : undefined}
        />
        {errors.address && <p id="reg-address-error" className="auth6-error" role="alert">{errors.address}</p>}
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
      <button className="auth6-submit" disabled={busy}>{busy ? 'Creating account...' : 'Create Account'}</button>
    </form>
  );
}

/* ─── Portal Home ──────────────────────────────────────────────────── */

function PortalHome({ patient, onLogout }) {
  const [screenings, setScreenings] = useState([]);
  const [screeningsLoading, setScreeningsLoading] = useState(true);
  const [selectedScreening, setSelectedScreening] = useState(null);

  useEffect(() => { loadScreenings(); }, []);

  function loadScreenings() {
    setScreeningsLoading(true);
    patientScreeningsAPI.mine()
      .then(r => setScreenings(r.data))
      .catch(() => toast.error('Could not load your screening history'))
      .finally(() => setScreeningsLoading(false));
  }

  if (selectedScreening) {
    return (
      <ScreeningDetailView
        screeningId={selectedScreening}
        onBack={() => setSelectedScreening(null)}
      />
    );
  }

  const latestScreening = screenings[0];

  function openAssistant() {
    window.dispatchEvent(new CustomEvent('tw-open-chat'));
  }

  const firstName = patient.full_name.split(' ')[0];

  const hasScreenings = screenings.length > 0;
  const riskLevel = latestScreening?.risk_level;
  const riskClass = riskLevel === 'HIGH' ? 'alert' : riskLevel === 'MEDIUM' ? 'warn' : 'good';
  const riskMsg = riskLevel === 'HIGH'
    ? 'Your latest screening found something that needs attention. Your dentist will follow up.'
    : riskLevel === 'MEDIUM'
    ? 'Your latest screening shows areas to keep an eye on. Nothing urgent, but worth a conversation.'
    : 'Your latest screening looks great. Keep up the good habits!';

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="pp2-shell">
      <header className="pp2-masthead">
        <div className="pp2-masthead-brand">
          <div className="pp2-masthead-logo">
            <LogoMark size={20} alt="CodiSmile Dental Clinic" />
          </div>
          <span className="pp2-masthead-name">ToothWise</span>
        </div>
        <button type="button" className="pp2-signout" onClick={onLogout}>
          <LogOut size={14} />
          Sign out
        </button>
      </header>

      {/* ── Greeting ── */}
        <section className="pp2-greet">
          <p className="pp2-greet-kicker">{greeting}</p>
          <h1 className="pp2-greet-name">{firstName}</h1>
          <p className="pp2-greet-sub">
            {hasScreenings
              ? `You have ${screenings.length} screening${screenings.length !== 1 ? 's' : ''} on record at ToothWise.`
              : 'Welcome to your dental health record. Your first screening will appear here after a visit.'}
          </p>
        </section>

        {/* ── Status card ── */}
        <section className={`pp2-status pp2-status--${hasScreenings ? riskClass : 'neutral'}`}>
          <div className="pp2-status-icon">
            {!hasScreenings ? <Microscope size={20} /> : riskClass === 'alert' ? <TriangleAlert size={20} /> : riskClass === 'warn' ? <AlertCircle size={20} /> : <CheckCircle size={20} />}
          </div>
          <div className="pp2-status-body">
            <span className="pp2-status-label">Dental health</span>
            <span className="pp2-status-value">{hasScreenings ? `${riskLevel} risk` : 'No data yet'}</span>
            <p className="pp2-status-msg">
              {hasScreenings ? riskMsg : 'Nothing to report yet. Once your dentist runs a screening, your summary will live here.'}
            </p>
          </div>
          <button type="button" className="pp2-status-cta" onClick={openAssistant}>
            Ask assistant <ChevronRight size={12} />
          </button>
        </section>

        {/* ── Quick facts ── */}
        <dl className="pp2-facts">
          <div className="pp2-fact">
            <dt className="pp2-fact-label">Last screening</dt>
            <dd className="pp2-fact-value">{hasScreenings ? formatDatePH(latestScreening.created_at) : 'Not yet'}</dd>
          </div>
          <div className="pp2-fact">
            <dt className="pp2-fact-label">Screenings on record</dt>
            <dd className="pp2-fact-value">{screenings.length}</dd>
          </div>
          <div className="pp2-fact">
            <dt className="pp2-fact-label">Assistant</dt>
            <dd className="pp2-fact-value">Ready when you are</dd>
          </div>
        </dl>

        {/* ── Screening history ── */}
        <section className="pp2-history" aria-labelledby="pp2-history-title">
          <div className="pp2-history-head">
            <h2 id="pp2-history-title" className="pp2-history-title">Screening history</h2>
            {hasScreenings && <span className="pp2-history-count">{screenings.length}</span>}
          </div>

          {screeningsLoading ? (
            <div className="pp2-screening-grid">
              {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} index={i} height={160} />)}
            </div>
          ) : screenings.length === 0 ? (
            <div className="pp2-empty">
              <div className="pp2-empty-icon">
                <Microscope size={28} />
              </div>
              <h3 className="pp2-empty-title">No screenings yet</h3>
              <p className="pp2-empty-text">Your dentist will add your first screening after a dental visit. Once added, you'll see your results and recommendations here.</p>
              <button type="button" className="pp2-empty-cta" onClick={openAssistant}>
                <MessageCircleQuestion size={14} />
                Ask the assistant
              </button>
            </div>
          ) : (
            <div className="pp2-screening-grid">
              {screenings.map((sc, i) => (
                <div
                  key={sc.id}
                  className="pp2-screening-card"
                  data-risk={sc.risk_level}
                  style={{ '--stagger-index': i }}
                  onClick={() => setSelectedScreening(sc.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedScreening(sc.id); } }}
                  aria-label={`Screening from ${formatDatePH(sc.created_at)}, ${sc.risk_level} risk`}
                >
                  <div className="pp2-screening-thumb-wrap">
                    <ScreeningThumbnail screeningId={sc.id} />
                    <span className={`pp2-risk-pill pp2-risk-pill--${sc.risk_level === 'HIGH' ? 'high' : sc.risk_level === 'MEDIUM' ? 'moderate' : 'low'}`}>
                      {sc.risk_level}
                    </span>
                  </div>
                  <div className="pp2-screening-card-body">
                    <div className="pp2-screening-card-meta">
                      <Clock size={11} />
                      <span>{formatDatePH(sc.created_at)}</span>
                    </div>
                    <span className="pp2-screening-card-cta">
                      View details <ChevronRight size={12} />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
    </div>
  );
}

/* ─── Screening Detail ─────────────────────────────────────────────── */

function ScreeningDetailView({ screeningId, onBack }) {
  const [screening, setScreening] = useState(null);
  const [loading, setLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState(null);

  useEffect(() => {
    patientScreeningsAPI.get(screeningId)
      .then(r => setScreening(r.data))
      .catch(err => toast.error(err.friendlyMessage || 'Could not load that screening'))
      .finally(() => setLoading(false));
  }, [screeningId]);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    patientScreeningsAPI.imageObjectUrl(screeningId).then(url => {
      if (cancelled) { window.URL.revokeObjectURL(url); return; }
      objectUrl = url;
      setImageUrl(url);
    }).catch(() => setImageUrl(null));
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [screeningId]);

  return (
    <div className="pp2-detail-page">
      <button type="button" className="pp2-back-btn" onClick={onBack}>
        <ArrowLeft size={14} />
        Back to screenings
      </button>

      {loading ? (
        <div className="pp2-detail-skeleton">
          <SkeletonBlock height={300} radius={16} />
          <SkeletonBlock width="50%" height={22} />
          <SkeletonBlock width="35%" height={16} />
        </div>
      ) : !screening ? (
        <div className="tw-state">
          <p className="tw-state__text">Screening not found.</p>
        </div>
      ) : (
        <div className="pp2-detail">
          <div className="pp2-detail-header">
            <div className="pp2-detail-title-row">
              <h2 className="pp2-detail-title">{formatDatePH(screening.created_at)}</h2>
              <span className={`pp2-risk-pill pp2-risk-pill--${screening.risk_level === 'HIGH' ? 'high' : screening.risk_level === 'MEDIUM' ? 'moderate' : 'low'}`}>
                {screening.risk_level} RISK
              </span>
            </div>
          </div>

          <div className="pp2-detail-grid">
            {/* Image */}
            <div className="pp2-detail-image">
              <BoundingBoxCanvas imageUrl={imageUrl} detections={screening.detections} />
            </div>

            {/* Info panel */}
            <div className="pp2-detail-info">
              {screening.detections?.length > 0 && (
                <div className="pp2-detail-block">
                  <h4 className="pp2-detail-block-title">
                    <Microscope size={14} />
                    Findings
                  </h4>
                  <div className="pp2-detection-chips">
                    {screening.detections.map((d, i) => (
                      <span key={i} className="pp2-detection-chip" style={{ '--chip-color': CLASS_COLORS[d.label] || '#6F5B61' }}>
                        <span className="pp2-detection-dot" />
                        {d.label.replace(/_/g, ' ')} {(d.confidence * 100).toFixed(0)}%
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {screening.recommendations?.length > 0 && (
                <div className="pp2-detail-block">
                  <h4 className="pp2-detail-block-title">
                    <Star size={14} />
                    Recommendations
                  </h4>
                  <ol className="pp2-rec-list">
                    {screening.recommendations
                      .sort((a, b) => a.order_index - b.order_index)
                      .map((r, i) => (
                        <li key={r.id} className="pp2-rec-item">
                          <span className="pp2-rec-num">{i + 1}</span>
                          <span className="pp2-rec-text">{r.text}</span>
                        </li>
                      ))}
                  </ol>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


