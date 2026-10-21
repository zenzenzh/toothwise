import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { MessageCircleQuestion, Microscope, TriangleAlert, ChevronRight, LogOut, Clock, CheckCircle, AlertCircle, ImageOff, CloudOff, RotateCw, TrendingDown, TrendingUp, Minus, CalendarClock, ListChecks, Search } from 'lucide-react';
import { patientScreeningsAPI } from '../../api';
import { formatDatePH } from '../../utils/datetime';
import { SkeletonCard } from '../../components/Skeleton';
import LogoMark from '../../components/LogoMark';
import EmptyState from '../../components/ui/EmptyState';
import Button from '../../components/ui/Button';
import { CLASS_COLORS_DEEP, prettyLabel } from '../../components/DetectionCanvas';
import PortalScreening, { riskPillClass } from './PortalScreening';
import RiskTrend from './RiskTrend';

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

// Most dentists recommend a routine checkup every six months.
const CHECKUP_MONTHS = 6;
const DAY = 864e5;

// Plain-language notes so a patient knows what each finding means.
const FINDING_NOTES = {
  cavity: 'Tooth decay. Your dentist may suggest a filling.',
  plaque: 'Soft buildup that daily brushing and flossing can clear.',
  tartar: 'Hardened buildup that needs a professional cleaning.',
  gum_inflammation: 'Irritated gums, often from plaque along the gumline.',
};

function timeAgo(iso) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / DAY);
  if (days < 1) return 'Today';
  if (days < 2) return 'Yesterday';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30.44);
  if (months < 12) return `${months} month${months !== 1 ? 's' : ''} ago`;
  const years = Math.floor(months / 12);
  return `Over ${years} year${years !== 1 ? 's' : ''} ago`;
}

function nextCheckup(lastIso) {
  const due = new Date(lastIso);
  due.setMonth(due.getMonth() + CHECKUP_MONTHS);
  const daysLeft = Math.ceil((due.getTime() - Date.now()) / DAY);
  if (daysLeft < 0) return { overdue: true, value: 'Overdue', sub: `Was due ${formatDatePH(due.toISOString(), { month: 'short', day: 'numeric', year: 'numeric' })}` };
  if (daysLeft <= 30) return { soon: true, value: 'Due soon', sub: `By ${formatDatePH(due.toISOString(), { month: 'short', day: 'numeric', year: 'numeric' })}` };
  return { value: formatDatePH(due.toISOString(), { month: 'long', year: 'numeric' }), sub: `${CHECKUP_MONTHS} months after your last visit` };
}

// How the latest screening compares with the one before it.
function compareToPrevious(latest, previous) {
  if (!previous) return null;
  const diff = latest.risk_score - previous.risk_score;
  if (diff <= -5) return { dir: 'down', Icon: TrendingDown, text: latest.risk_level !== previous.risk_level ? `Improved from ${previous.risk_level.toLowerCase()} risk last time` : 'Lower than your previous screening' };
  if (diff >= 5) return { dir: 'up', Icon: TrendingUp, text: latest.risk_level !== previous.risk_level ? `Up from ${previous.risk_level.toLowerCase()} risk last time` : 'Higher than your previous screening' };
  return { dir: 'same', Icon: Minus, text: 'About the same as your previous screening' };
}

function groupFindings(detections = []) {
  const counts = {};
  let healthy = 0;
  for (const d of detections) {
    if (d.label === 'healthy_tooth') healthy += 1;
    else counts[d.label] = (counts[d.label] || 0) + 1;
  }
  const issues = Object.entries(counts)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count);
  return { issues, healthy };
}

function findingSummary(detections) {
  const n = (detections || []).filter(d => d.label !== 'healthy_tooth').length;
  return n === 0 ? 'No problem areas' : `${n} area${n !== 1 ? 's' : ''} to watch`;
}

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
  const change = hasScreenings ? compareToPrevious(latest, screenings[1]) : null;
  const checkup = hasScreenings ? nextCheckup(latest.created_at) : null;
  const findings = hasScreenings ? groupFindings(latest.detections) : null;
  const nextSteps = hasScreenings
    ? [...(latest.recommendations || [])].sort((a, b) => a.order_index - b.order_index).slice(0, 3)
    : [];
  const ChangeIcon = change?.Icon;

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
              {change && (
                <p className={`pp2-status-change pp2-status-change--${change.dir}`}>
                  <ChangeIcon size={14} aria-hidden="true" />
                  {change.text}
                </p>
              )}
            </div>
            <div className="pp2-status-actions">
              {hasScreenings && (
                <button type="button" className="pp2-status-cta" onClick={() => openScreening(latest.id)}>
                  View results <ChevronRight size={12} aria-hidden="true" />
                </button>
              )}
              <button type="button" className={`pp2-status-cta${hasScreenings ? ' pp2-status-cta--ghost' : ''}`} onClick={openAssistant}>
                <MessageCircleQuestion size={14} aria-hidden="true" />
                Ask assistant
              </button>
            </div>
          </section>
        )}

        {!loadError && (
          <dl className="pp2-facts">
            <div className="pp2-fact">
              <dt className="pp2-fact-label">Last screening</dt>
              <dd className="pp2-fact-value">{loading ? '—' : hasScreenings ? formatDatePH(latest.created_at) : 'Not yet'}</dd>
              {!loading && hasScreenings && <dd className="pp2-fact-sub">{timeAgo(latest.created_at)}</dd>}
            </div>
            <div className={`pp2-fact${checkup?.overdue ? ' pp2-fact--alert' : checkup?.soon ? ' pp2-fact--warn' : ''}`}>
              <dt className="pp2-fact-label">
                <CalendarClock size={13} aria-hidden="true" />
                Next checkup
              </dt>
              <dd className="pp2-fact-value">{loading ? '—' : checkup ? checkup.value : 'After your first visit'}</dd>
              {!loading && checkup && <dd className="pp2-fact-sub">{checkup.sub}</dd>}
            </div>
            <div className="pp2-fact">
              <dt className="pp2-fact-label">Screenings on record</dt>
              <dd className="pp2-fact-value">{loading ? '—' : screenings.length}</dd>
              {!loading && screenings.length > 1 && (
                <dd className="pp2-fact-sub">Since {formatDatePH(screenings[screenings.length - 1].created_at, { month: 'short', year: 'numeric' })}</dd>
              )}
            </div>
          </dl>
        )}

        {!loadError && !loading && hasScreenings && (
          <section className="pp2-latest" aria-labelledby="pp2-latest-title">
            <div className="pp2-section-head">
              <h2 id="pp2-latest-title" className="pp2-section-title">Your latest results</h2>
              <button type="button" className="pp2-text-link" onClick={() => openScreening(latest.id)}>
                See photo and details <ChevronRight size={12} aria-hidden="true" />
              </button>
            </div>
            <div className="pp2-latest-grid">
              <div className="pp2-panel">
                <h3 className="pp2-panel-title">
                  <Search size={14} aria-hidden="true" />
                  What we found
                </h3>
                {findings.issues.length > 0 ? (
                  <ul className="pp2-findings">
                    {findings.issues.map(f => (
                      <li key={f.label} className="pp2-finding">
                        <span className="pp2-finding-dot" style={{ '--dot': CLASS_COLORS_DEEP[f.label] || '#6F5B61' }} aria-hidden="true" />
                        <span className="pp2-finding-body">
                          <span className="pp2-finding-name">
                            {prettyLabel(f.label)}
                            {f.count > 1 && <span className="pp2-finding-count">{f.count} areas</span>}
                          </span>
                          {FINDING_NOTES[f.label] && <span className="pp2-finding-note">{FINDING_NOTES[f.label]}</span>}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="pp2-panel-empty">No problem areas were spotted in this screening.</p>
                )}
                {findings.healthy > 0 && (
                  <p className="pp2-findings-healthy">
                    <CheckCircle size={14} aria-hidden="true" />
                    {findings.healthy} healthy {findings.healthy === 1 ? 'tooth' : 'teeth'} spotted
                  </p>
                )}
              </div>
              <div className="pp2-panel">
                <h3 className="pp2-panel-title">
                  <ListChecks size={14} aria-hidden="true" />
                  Your next steps
                </h3>
                {nextSteps.length > 0 ? (
                  <ol className="pp2-steps">
                    {nextSteps.map((r, i) => (
                      <li key={r.id} className="pp2-step">
                        <span className="pp2-step-num" aria-hidden="true">{i + 1}</span>
                        <span>{r.text}</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="pp2-panel-empty">No extra steps for now. Keep brushing twice a day and flossing daily.</p>
                )}
                {(latest.recommendations?.length || 0) > nextSteps.length && (
                  <button type="button" className="pp2-text-link" onClick={() => openScreening(latest.id)}>
                    {latest.recommendations.length - nextSteps.length} more in your full results <ChevronRight size={12} aria-hidden="true" />
                  </button>
                )}
              </div>
            </div>
            <p className="pp2-latest-note">AI-assisted results, reviewed by your dentist. Not a diagnosis.</p>
          </section>
        )}

        {!loadError && !loading && screenings.length > 1 && (
          <section className="pp2-trend" aria-labelledby="pp2-trend-title">
            <div className="pp2-section-head">
              <h2 id="pp2-trend-title" className="pp2-section-title">Risk over time</h2>
              <span className="pp2-section-meta">Risk score, 0 to 100. Lower is better.</span>
            </div>
            <div className="pp2-panel pp2-panel--chart">
              <RiskTrend screenings={screenings} onOpen={openScreening} />
            </div>
          </section>
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
                    aria-label={`Screening from ${formatDatePH(sc.created_at)}, ${sc.risk_level} risk, ${findingSummary(sc.detections).toLowerCase()}. View details`}
                  >
                    <span className="pp2-screening-thumb-wrap">
                      <ScreeningThumbnail screeningId={sc.id} />
                      <span className={riskPillClass(sc.risk_level)}>{sc.risk_level}</span>
                    </span>
                    <span className="pp2-screening-card-body">
                      <span className="pp2-screening-card-info">
                        <span className="pp2-screening-card-meta">
                          <Clock size={11} aria-hidden="true" />
                          <span>{formatDatePH(sc.created_at, { month: 'short' })}</span>
                        </span>
                        <span className="pp2-screening-card-findings">{findingSummary(sc.detections)}</span>
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
