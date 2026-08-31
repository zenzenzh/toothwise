import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Activity, MessageCircleQuestion, Microscope, TriangleAlert, CalendarDays } from 'lucide-react';
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

const BURGUNDY = '#4B2F35';
const ROSE = '#BA7976';
const ROSEGOLD = '#C78C8A';
const BLUSH = '#FBF7F5';
const WHITE = '#FFFFFF';
const MUTED = '#6F5B61';

// Matches app/ml/labels.py LABELS on the backend / ScreeningDetail.jsx on the staff side.
const CLASS_COLORS = {
  healthy_tooth:       '#22C55E',
  cavity:              '#EF4444',
  gum_inflammation:    '#F97316',
  plaque:              '#EAB308',
  tartar:              '#B45309',
};

const RISK_STYLE = {
  HIGH:   { background: '#FCE8EA', color: '#C4505A', border: '1px solid #F5C0C4' },
  MEDIUM: { background: '#FEF3E2', color: '#D4850A', border: '1px solid #F9DBA0' },
  LOW:    { background: '#E8F5EE', color: '#2D7A52', border: '1px solid #A8DBBE' },
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

        const color = CLASS_COLORS[d.label] || '#FF0000';
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
    <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', background: '#f0f0f0', width: '100%' }}>
      <img src={imageUrl} alt="Screening" style={{ width: '100%', display: imgLoaded ? 'none' : 'block' }} />
      <canvas ref={canvasRef} style={{ width: '100%', display: imgLoaded ? 'block' : 'none', height: 'auto' }} />
    </div>
  );
}

// Each thumbnail fetches its own authenticated image (there's no
// unauthenticated static path for these anymore) and cleans up its
// object URL when it unmounts or the screening it's showing changes -
// important here since a whole grid of these can be on screen together.
function ScreeningThumbnail({ screeningId, style }) {
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

  if (!url) return <div style={{ ...style, background: BLUSH }} />;
  return <img src={url} alt="Screening" style={style} />;
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
        <div style={s.page}>
          <div style={s.circle1} />
          <div style={s.circle2} />
          <PortalHome patient={patient} onLogout={handleLogout} />
        </div>
      ) : (
        <AuthCard />
      )}
      <ChatWidget patient={patient} />
    </>
  );
}

// Shared with the staff login screen (pages/Login.jsx + components/AuthLayout.jsx)
// so both auth surfaces use the identical split-screen layout and field styling.
const authField = 'auth6-field';
const authLabel = 'auth6-label';
// Some labels in the name row wrap to two lines ("Middle Name / Initial")
// while their siblings ("First Name", "Last Name") stay on one line. Without
// a shared minimum height the inputs below them end up at different vertical
// positions. This variant reserves two lines of height for every label in
// that row so all three inputs line up.
const authLabelRow = 'auth6-label auth6-label-row';
const authFieldError = { color: '#C23F4A', fontSize: 11, margin: 0 };
const authHint = { fontSize: 11, color: '#6F5B61', margin: '4px 0 0 0' };

function AuthCard() {
  const [mode, setMode] = useState('login'); // 'login' | 'register'

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
      <div className={authField}>
        <label htmlFor="portal-login-email" className={authLabel}>Email Address</label>
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
        />
        {errors.email && <p style={authFieldError} role="alert">{errors.email}</p>}
      </div>
      <PasswordField
        value={password}
        onChange={v => { setPassword(v); if (errors.password) setErrors({}); }}
        autoComplete="current-password"
        error={errors.password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName={authLabel}
        fieldClassName={authField}
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

    // Real validation, not just "is it non-empty" - a made-up email or a
    // random string of digits for a phone number is rejected here before
    // it ever reaches the backend, with a specific reason shown per field.
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
        <div className={authField}>
          <label htmlFor="reg-first-name" className={authLabelRow}>First Name</label>
          <input
            id="reg-first-name"
            className="auth6-input"
            value={form.first_name}
            onChange={e => set('first_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="given-name"
            required
            aria-invalid={!!errors.first_name}
          />
          {errors.first_name && <p style={authFieldError} role="alert">{errors.first_name}</p>}
        </div>
        <div className={authField}>
          <label htmlFor="reg-middle-name" className={authLabelRow}>Middle Name / Initial</label>
          <input
            id="reg-middle-name"
            className="auth6-input"
            value={form.middle_name}
            onChange={e => set('middle_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="additional-name"
            aria-invalid={!!errors.middle_name}
          />
          {errors.middle_name && <p style={authFieldError} role="alert">{errors.middle_name}</p>}
        </div>
        <div className={`${authField} auth6-span-2`}>
          <label htmlFor="reg-last-name" className={authLabel}>Last Name</label>
          <input
            id="reg-last-name"
            className="auth6-input"
            value={form.last_name}
            onChange={e => set('last_name', e.target.value)}
            maxLength={LIMITS.NAME_MAX}
            autoComplete="family-name"
            required
            aria-invalid={!!errors.last_name}
          />
          {errors.last_name && <p style={authFieldError} role="alert">{errors.last_name}</p>}
        </div>
      </div>
      <div className={authField}>
        <label htmlFor="reg-email" className={authLabel}>Email Address</label>
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
        />
        {errors.email && <p style={authFieldError} role="alert">{errors.email}</p>}
      </div>
      <div className={authField}>
        <label htmlFor="reg-phone" className={authLabel}>Mobile Number</label>
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
        />
        {errors.contact_number && <p style={authFieldError} role="alert">{errors.contact_number}</p>}
        <p style={authHint}>Used by the clinic to reach you about your records.</p>
      </div>
      <div className="auth6-grid auth6-grid-2">
        <div className={authField}>
          <label htmlFor="reg-gender" className={authLabel}>Gender</label>
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
        <div className={authField}>
          <label htmlFor="reg-birthdate" className={authLabel}>Birthdate</label>
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
          />
          {errors.birthdate && <p style={authFieldError} role="alert">{errors.birthdate}</p>}
        </div>
      </div>
      <div className={authField}>
        <label htmlFor="reg-address" className={authLabel}>Address</label>
        <input
          id="reg-address"
          className="auth6-input"
          value={form.address}
          onChange={e => set('address', e.target.value)}
          maxLength={LIMITS.ADDRESS_MAX}
          autoComplete="street-address"
          aria-invalid={!!errors.address}
        />
        {errors.address && <p style={authFieldError} role="alert">{errors.address}</p>}
      </div>
      <PasswordField
        value={form.password}
        onChange={v => set('password', v)}
        showRequirements
        error={errors.password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName={authLabel}
        fieldClassName={authField}
      />
      <PasswordField
        value={form.confirm_password}
        onChange={v => set('confirm_password', v)}
        label="Confirm Password"
        error={errors.confirm_password}
        inputClassName="auth6-input auth6-input-password"
        labelClassName={authLabel}
        fieldClassName={authField}
      />
      <button className="auth6-submit" disabled={busy}>{busy ? 'Creating account...' : 'Create Account'}</button>
    </form>
  );
}

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

  return (
    <div style={s.homeCard}>
      <div style={s.homeHeader}>
        <div style={{ minWidth: 0 }}>
          <div style={s.homeBrandRow}>
            <span style={s.homeMark}><Activity size={15} /></span>
            <span style={s.homeBrand}>ToothWise</span>
          </div>
          <h1 style={s.homeGreeting}>Hi, {patient.full_name.split(' ')[0]}</h1>
          <p style={s.homeSub}>Here's where your dental care stands.</p>
        </div>
        <button style={s.logoutBtn} onClick={onLogout}>Log out</button>
      </div>

      {/* Stats cards grid */}
      <div style={s.statsGrid} className="tw6-portal-stats">
        <div style={s.statCard}>
          <div style={s.statIcon}><Microscope size={18} /></div>
          <div style={s.statValue}>{screeningsLoading ? '—' : screenings.length}</div>
          <div style={s.statLabel}>Screenings on file</div>
        </div>
        <div style={s.statCard}>
          <div style={{ ...s.statIcon, ...(latestScreening?.risk_level === 'HIGH' ? s.statIconDanger : {}) }}>
            <TriangleAlert size={18} />
          </div>
          <div style={s.statValue}>
            {screeningsLoading ? '—' : latestScreening ? (
              <span style={{ ...s.riskBadge, ...RISK_STYLE[latestScreening.risk_level] }}>{latestScreening.risk_level}</span>
            ) : 'No data yet'}
          </div>
          <div style={s.statLabel}>Latest risk level</div>
        </div>
        <div style={s.statCard}>
          <div style={s.statIcon}><CalendarDays size={18} /></div>
          <div style={s.statValue}>{screeningsLoading ? '—' : latestScreening ? formatDatePH(latestScreening.created_at) : 'None yet'}</div>
          <div style={s.statLabel}>Last screening</div>
        </div>
      </div>

      <div style={s.assistantCta} className="tw-portal-cta">
        <div style={s.assistantCtaText}><MessageCircleQuestion size={17} /> Have a question about your results?</div>
        <button style={s.assistantCtaBtn} onClick={openAssistant}>Ask the assistant</button>
      </div>

      <div style={s.listSection}>
        <h3 style={s.sectionTitle}>Your screening history</h3>
        {screeningsLoading ? (
          <div style={s.screeningGrid}>
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} index={i} height={160} />)}
          </div>
        ) : screenings.length === 0 ? (
          <div style={s.emptyState}>
            <div style={s.emptyIcon}><CalendarDays size={32} /></div>
            <p style={s.emptyTitle}>No screenings yet</p>
            <p style={s.hint}>Your dentist will add one after a visit.</p>
          </div>
        ) : (
          <div style={s.screeningGrid}>
            {screenings.map((sc, i) => (
              <div key={sc.id} className="stagger-item tw6-portal-card" style={{ ...s.screeningCard, '--stagger-index': i }} onClick={() => setSelectedScreening(sc.id)}>
                <ScreeningThumbnail screeningId={sc.id} style={s.screeningThumb} />
                <div style={s.screeningCardBody}>
                  <div style={s.screeningDate}>
                    {formatDatePH(sc.created_at)}
                  </div>
                  <span style={{ ...s.riskBadge, ...RISK_STYLE[sc.risk_level] }}>{sc.risk_level} RISK</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

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
    <div style={s.homeCard}>
      <button style={s.logoutBtn} onClick={onBack}>← Back</button>
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 16 }}>
          <SkeletonBlock height={200} radius={12} />
          <SkeletonBlock width="60%" height={16} />
          <SkeletonBlock width="40%" height={16} />
        </div>
      ) : !screening ? (
        <p style={{ ...s.hint, marginTop: 16 }}>Screening not found.</p>
      ) : (
        <div style={{ marginTop: 16 }}>
          <div style={s.screeningDetailHeader}>
            <h3 style={s.sectionTitle}>
              {formatDatePH(screening.created_at)}
            </h3>
            <span style={{ ...s.riskBadge, ...RISK_STYLE[screening.risk_level] }}>{screening.risk_level} RISK</span>
          </div>

          <BoundingBoxCanvas
            imageUrl={imageUrl}
            detections={screening.detections}
          />

          {screening.recommendations?.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h4 style={s.sectionTitle}>Recommendations</h4>
              <ul style={s.recList}>
                {screening.recommendations
                  .sort((a, b) => a.order_index - b.order_index)
                  .map(r => <li key={r.id} style={s.recItem}>{r.text}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const s = {
  page: {
    minHeight: '100vh',
    background: `linear-gradient(135deg, #FBF7F5 0%, #EDE0E8 40%, #E5DADC 100%)`,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    position: 'relative', overflow: 'auto', padding: '40px 16px',
    fontFamily: "Inter, 'Segoe UI', Arial, sans-serif",
  },
  circle1: { position: 'absolute', top: -120, right: -120, width: 400, height: 400, borderRadius: '50%', background: 'rgba(196,132,126,0.12)', pointerEvents: 'none' },
  circle2: { position: 'absolute', bottom: -80, left: -80, width: 300, height: 300, borderRadius: '50%', background: 'rgba(92,58,74,0.08)', pointerEvents: 'none' },
  card: {
    background: WHITE, borderRadius: 24, padding: '48px 44px', width: 420,
    textAlign: 'center', boxShadow: '0 20px 60px rgba(92,58,74,0.15), 0 4px 20px rgba(92,58,74,0.08)',
    position: 'relative', zIndex: 1,
  },
  homeCard: {
    background: WHITE, borderRadius: 24, padding: 'clamp(20px, 4vw, 32px)', width: '100%', maxWidth: 760,
    border: '1px solid #E5DADC',
    boxShadow: '0 24px 70px rgba(75,47,53,0.12)',
    position: 'relative', zIndex: 1, boxSizing: 'border-box',
  },
  homeHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 22 },
  homeBrandRow: { display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 },
  homeMark: {
    width: 24, height: 24, borderRadius: 8, background: BURGUNDY, color: WHITE,
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
  },
  homeBrand: { fontSize: 12.5, fontWeight: 700, color: BURGUNDY, letterSpacing: '0.02em' },
  homeGreeting: { fontSize: 26, fontWeight: 700, color: BURGUNDY, letterSpacing: '-0.02em', margin: 0 },
  homeSub: { fontSize: 13, color: MUTED, margin: '4px 0 0 0' },
  logoutBtn: {
    background: 'transparent', border: `1.5px solid ${ROSEGOLD}`, borderRadius: 9,
    color: BURGUNDY, padding: '9px 16px', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
    minHeight: 40,
  },
  statsRow: {
    display: 'grid', gap: 0,
    borderTop: '1px solid #F0E4E2', borderBottom: '1px solid #F0E4E2',
    marginBottom: 22,
  },
  statCell: { padding: '15px 18px', borderLeft: '1px solid #F0E4E2', minWidth: 0 },
  statLabel: { fontSize: 10, color: MUTED, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em' },
  statValue: { fontSize: 14.5, color: BURGUNDY, fontWeight: 700, marginTop: 5 },
  assistantCta: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
    background: BURGUNDY, borderRadius: 14, padding: '15px 18px',
    marginBottom: 22, color: WHITE,
  },
  assistantCtaText: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, fontWeight: 600 },
  assistantCtaBtn: {
    background: 'rgba(255,255,255,0.14)', border: '1px solid rgba(255,255,255,0.35)', borderRadius: 9,
    color: WHITE, padding: '9px 16px', fontSize: 12, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', flexShrink: 0,
    minHeight: 40,
  },
  screeningGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 12 },
  screeningCard: {
    background: BLUSH, borderRadius: 14, overflow: 'hidden', cursor: 'pointer',
    border: `1px solid #E5DADC`, transition: 'transform 180ms ease, box-shadow 180ms ease',
  },
  screeningThumb: { width: '100%', height: 120, objectFit: 'cover', display: 'block' },
  screeningCardBody: { padding: '10px 12px' },
  screeningDate: { fontSize: 12, color: BURGUNDY, fontWeight: 600, marginBottom: 6 },
  riskBadge: { fontSize: 10, fontWeight: 800, padding: '4px 10px', borderRadius: 20, letterSpacing: '0.03em' },
  screeningDetailHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 14 },
  recList: { margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 8 },
  recItem: { fontSize: 13, color: BURGUNDY, lineHeight: 1.5 },
  sectionTitle: { fontSize: 15, color: BURGUNDY, fontWeight: 700, margin: '0 0 14px 0', letterSpacing: '0.03em' },
  listSection: {},
  logoWrap: { display: 'flex', justifyContent: 'center', marginBottom: 16 },
  logoRing: {
    width: 80, height: 80, borderRadius: '50%',
    background: `linear-gradient(135deg, ${BURGUNDY}, ${ROSE})`,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: `0 8px 24px rgba(92,58,74,0.3)`,
  },
  logoIcon: { fontSize: 36 },
  brand: { fontFamily: "Inter, 'Segoe UI', Arial, sans-serif", fontSize: 26, fontWeight: 700, color: BURGUNDY, letterSpacing: '0.15em', margin: '0 0 4px 0' },
  clinic: { fontSize: 15, color: ROSE, fontWeight: 600, margin: '0 0 4px 0', letterSpacing: '0.05em' },
  tagline: { fontSize: 12, color: MUTED, margin: '0 0 20px 0' },
  divider: { height: 1, background: `linear-gradient(90deg, transparent, ${ROSEGOLD}, transparent)`, margin: '0 0 24px 0' },
  form: { display: 'flex', flexDirection: 'column', gap: 16, textAlign: 'left' },
  hint: { fontSize: 11, color: MUTED, margin: '2px 0 0 0' },
  switchText: { fontSize: 12, color: MUTED, marginTop: 20 },
  switchLink: { color: BURGUNDY, fontWeight: 700, cursor: 'pointer', textDecoration: 'underline' },
};
