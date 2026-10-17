import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageCircleQuestion, Microscope, TriangleAlert, ChevronRight, LogOut, Clock, CheckCircle, AlertCircle, ImageOff, CloudOff, RotateCw } from 'lucide-react';
import { patientScreeningsAPI } from '../../api';
import { formatDatePH } from '../../utils/datetime';
import { SkeletonCard } from '../../components/Skeleton';
import LogoMark from '../../components/LogoMark';
import EmptyState from '../../components/ui/EmptyState';
import Button from '../../components/ui/Button';
import PortalScreening, { riskPillClass } from './PortalScreening';

function ScreeningThumbnail({ screeningId }) {
  const [url, setUrl] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    patientScreeningsAPI.imageObjectUrl(screeningId).then(u => {
      if (cancelled) { window.URL.revokeObjectURL(u); return; }
      objectUrl = u;
      setUrl(u);
    }).catch(() => { if (!cancelled) setFailed(true); });
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [screeningId]);

  if (failed) return <div className="pp-thumb pp-thumb--failed"><ImageOff size={22} aria-hidden="true" /></div>;
  if (!url) return <div className="pp-thumb pp-thumb--skeleton" />;
  return <img src={url} alt="" className="pp-thumb" loading="lazy" />;
}

const RISK_COPY = {
  HIGH: { tone: 'alert', Icon: TriangleAlert, msg: 'Your latest screening found something that needs attention. Your dentist will follow up.' },
  MEDIUM: { tone: 'warn', Icon: AlertCircle, msg: 'Your latest screening shows areas to keep an eye on. Nothing urgent, but worth a conversation.' },
  LOW: { tone: 'good', Icon: CheckCircle, msg: 'Your latest screening looks great. Keep up the good habits!' },
};

export default function PortalHome({ patient, onLogout }) {
  const [screenings, setScreenings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  // The open screening lives in the URL (?screening=12) so the browser's
  // Back button closes it instead of leaving the portal.
  const [params, setParams] = useSearchParams();
  const selected = params.get('screening');

  const loadScreenings = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    patientScreeningsAPI.mine()
      .then(r => setScreenings(r.data))
      .catch(err => setLoadError(err.friendlyMessage || 'Your screening history could not be loaded.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadScreenings(); }, [loadScreenings]);

  useEffect(() => { window.scrollTo(0, 0); }, [selected]);

  const openScreening = id => setParams({ screening: String(id) });
  const closeScreening = () => {
    // Prefer history back when we pushed the entry ourselves.
    if (window.history.state?.idx > 0) window.history.back();
    else setParams({}, { replace: true });
  };

  if (selected) {
    return <PortalScreening screeningId={selected} onBack={closeScreening} />;
  }

  const openAssistant = () => window.dispatchEvent(new CustomEvent('tw-open-chat'));

  const latest = screenings[0];
  const firstName = patient.full_name.split(' ')[0];
  const hasScreenings = screenings.length > 0;
  const risk = hasScreenings ? (RISK_COPY[latest.risk_level] || RISK_COPY.LOW) : null;
  const StatusIcon = risk ? risk.Icon : Microscope;

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
          <LogOut size={14} aria-hidden="true" />
          Sign out
        </button>
      </header>

      <main>
        <section className="pp2-greet">
          <p className="pp2-greet-kicker">{greeting}</p>
          <h1 className="pp2-greet-name">{firstName}</h1>
          <p className="pp2-greet-sub">
            {loadError
              ? 'Your dental health record is temporarily unavailable.'
              : loading
              ? 'Loading your dental health record…'
              : hasScreenings
                ? `You have ${screenings.length} screening${screenings.length !== 1 ? 's' : ''} on record at ToothWise.`
                : 'Welcome to your dental health record. Your first screening will appear here after a visit.'}
          </p>
        </section>

        {!loadError && !loading && (
          <section className={`pp2-status pp2-status--${risk ? risk.tone : 'neutral'}`} aria-label="Dental health summary">
            <div className="pp2-status-icon" aria-hidden="true"><StatusIcon size={20} /></div>
            <div className="pp2-status-body">
              <span className="pp2-status-label">Dental health</span>
              <span className="pp2-status-value">{risk ? `${latest.risk_level} risk` : 'No data yet'}</span>
              <p className="pp2-status-msg">
                {risk ? risk.msg : 'Nothing to report yet. Once your dentist runs a screening, your summary will live here.'}
              </p>
            </div>
            <button type="button" className="pp2-status-cta" onClick={openAssistant}>
              Ask assistant <ChevronRight size={12} aria-hidden="true" />
            </button>
          </section>
        )}

        {!loadError && (
          <dl className="pp2-facts">
            <div className="pp2-fact">
              <dt className="pp2-fact-label">Last screening</dt>
              <dd className="pp2-fact-value">{loading ? '—' : hasScreenings ? formatDatePH(latest.created_at) : 'Not yet'}</dd>
            </div>
            <div className="pp2-fact">
              <dt className="pp2-fact-label">Screenings on record</dt>
              <dd className="pp2-fact-value">{loading ? '—' : screenings.length}</dd>
            </div>
            <div className="pp2-fact">
              <dt className="pp2-fact-label">Assistant</dt>
              <dd className="pp2-fact-value">Ready when you are</dd>
            </div>
          </dl>
        )}

        <section className="pp2-history" aria-labelledby="pp2-history-title">
          <div className="pp2-history-head">
            <h2 id="pp2-history-title" className="pp2-history-title">Screening history</h2>
            {hasScreenings && <span className="pp2-history-count">{screenings.length}</span>}
          </div>

          {loadError ? (
            <EmptyState
              className="tw-state--card"
              role="alert"
              icon={CloudOff}
              title="Couldn't load your screenings"
              message={loadError}
              action={<Button variant="secondary" icon={RotateCw} onClick={loadScreenings}>Try again</Button>}
            />
          ) : loading ? (
            <div className="pp2-screening-grid" aria-busy="true" aria-label="Loading screenings">
              {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} index={i} height={160} />)}
            </div>
          ) : !hasScreenings ? (
            <div className="pp2-empty">
              <div className="pp2-empty-icon" aria-hidden="true"><Microscope size={28} /></div>
              <h3 className="pp2-empty-title">No screenings yet</h3>
              <p className="pp2-empty-text">Your dentist will add your first screening after a dental visit. Once added, you'll see your results and recommendations here.</p>
              <button type="button" className="pp2-empty-cta" onClick={openAssistant}>
                <MessageCircleQuestion size={14} aria-hidden="true" />
                Ask the assistant
              </button>
            </div>
          ) : (
            <ul className="pp2-screening-grid">
              {screenings.map((sc, i) => (
                <li key={sc.id}>
                  <button
                    type="button"
                    className="pp2-screening-card"
                    data-risk={sc.risk_level}
                    style={{ '--stagger-index': i }}
                    onClick={() => openScreening(sc.id)}
                    aria-label={`Screening from ${formatDatePH(sc.created_at)}, ${sc.risk_level} risk. View details`}
                  >
                    <span className="pp2-screening-thumb-wrap">
                      <ScreeningThumbnail screeningId={sc.id} />
                      <span className={riskPillClass(sc.risk_level)}>{sc.risk_level}</span>
                    </span>
                    <span className="pp2-screening-card-body">
                      <span className="pp2-screening-card-meta">
                        <Clock size={11} aria-hidden="true" />
                        <span>{formatDatePH(sc.created_at)}</span>
                      </span>
                      <span className="pp2-screening-card-cta">
                        View details <ChevronRight size={12} aria-hidden="true" />
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
