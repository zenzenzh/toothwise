import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ScanSearch, ScanLine, ArrowUpRight, UserX, CloudOff, RotateCw, Lock } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceArea } from 'recharts';
import { patientsAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { can } from '../utils/permissions';
import { formatDatePH, formatShortDatePH } from '../utils/datetime';
import { SkeletonBlock, SkeletonCircle, SkeletonCard } from '../components/Skeleton';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import RiskBadge, { RISK_COLOR } from '../components/ui/RiskBadge';
import T from '../tokens';

// Trend chart shows severity level, never the raw internal score - the
// score still drives point height (so a genuine within-band change is
// still visible as movement), but nothing on screen prints a number.
function RiskTrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { date, level } = payload[0].payload;
  return (
    <div className="pd6-tooltip">
      <div className="pd6-tooltip-date">{date}</div>
      <RiskBadge level={level} size="sm" />
    </div>
  );
}

function riskTrendDot(props) {
  const { cx, cy, payload, index } = props;
  return <circle key={index} cx={cx} cy={cy} r={5.5} fill={RISK_COLOR[payload.level] || T.accent} stroke={T.surface} strokeWidth={2} />;
}

function DetailSkeleton() {
  return (
    <div className="tw-page-layout" aria-busy="true" aria-label="Loading patient">
      <SkeletonBlock width={160} height={40} radius={10} />
      <div className="pd6-skeleton-head">
        <SkeletonCircle size={72} />
        <div style={{ flex: 1 }}>
          <SkeletonBlock width={200} height={22} />
          <SkeletonBlock width={140} height={13} style={{ marginTop: 8 }} />
        </div>
      </div>
      <SkeletonCard index={0} height={150} />
      <SkeletonCard index={1} height={220} />
    </div>
  );
}

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dentist: me } = useAuth();
  // Receptionists may view the patient record but not clinical data
  // (screening history / risk trend), which the API also enforces.
  const canViewClinical = can(me?.role, 'clinical');
  const [patient, setPatient] = useState(null);
  const [screenings, setScreenings] = useState([]);
  const [riskTrend, setRiskTrend] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // { notFound, message }
  const [clinicalError, setClinicalError] = useState(null);

  const load = useCallback(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setClinicalError(null);
    setPatient(null);
    setScreenings([]);
    setRiskTrend([]);

    // The patient record is required; history and trend load alongside it
    // but a failure there only affects their own section.
    const clinical = canViewClinical
      ? Promise.allSettled([patientsAPI.screenings(id), patientsAPI.riskTrend(id)])
      : Promise.resolve(null);

    Promise.all([patientsAPI.get(id), clinical])
      .then(([p, results]) => {
        if (cancelled) return;
        setPatient(p.data);
        if (results) {
          const [s, t] = results;
          if (s.status === 'fulfilled') setScreenings(s.value.data);
          else setClinicalError(s.reason?.friendlyMessage || 'Screening history could not be loaded.');
          if (t.status === 'fulfilled') setRiskTrend(t.value.data);
        }
      })
      .catch(err => {
        if (cancelled) return;
        setError({
          notFound: err.response?.status === 404,
          message: err.friendlyMessage || 'The patient record could not be loaded.',
        });
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [id, canViewClinical]);

  useEffect(() => load(), [load]);

  const backButton = (
    <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/dashboard/patients')}>Back to Patients</Button>
  );

  if (loading) return <DetailSkeleton />;

  if (error) {
    return (
      <div className="tw-page-layout">
        <div className="tw-page-header">{backButton}</div>
        {error.notFound ? (
          <EmptyState
            className="tw-state--card"
            icon={UserX}
            title="Patient record not found"
            message="The patient may have been removed, or you may no longer have access to this record."
          />
        ) : (
          <EmptyState
            className="tw-state--card"
            role="alert"
            icon={CloudOff}
            title="Couldn't load this patient"
            message={error.message}
            action={<Button variant="secondary" icon={RotateCw} onClick={load}>Try again</Button>}
          />
        )}
      </div>
    );
  }

  const startScreening = () => navigate(`/dashboard/patients/${id}/screening`);
  const latestLevel = screenings[0]?.risk_level;
  const details = [
    { label: 'Age',     value: patient.age != null ? patient.age + ' years old' : '—' },
    { label: 'Gender',  value: patient.gender || '—' },
    { label: 'Contact', value: patient.contact_number || '—' },
    { label: 'Address', value: patient.address || '—' },
  ];

  return (
    <div className="tw-page-layout">
      <div className="tw-page-header">
        {backButton}
        {canViewClinical && <Button icon={ScanLine} onClick={startScreening}>New Screening</Button>}
      </div>

      {/* Profile header: avatar + identity left, latest risk right */}
      <section className="pd6-card pd6-profile" aria-label="Patient">
        <div className="pd6-identity">
          <div className="tw-avatar tw-avatar--lg" aria-hidden="true">{patient.full_name.charAt(0)}</div>
          <div className="pd6-identity-text">
            <h1 className="pd6-name">{patient.full_name}</h1>
            <p className="pd6-id">Patient ID #{patient.id}</p>
          </div>
        </div>
        {latestLevel && (
          <div className="pd6-latest">
            <span className="pd6-eyebrow">Latest result</span>
            <RiskBadge level={latestLevel} size="lg" />
          </div>
        )}
      </section>

      {/* Details as a ruled definition list, not tiles */}
      <dl className="pd6-card pd6-defs">
        {details.map(item => (
          <div key={item.label} className="pd6-def">
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>

      {canViewClinical && riskTrend.length >= 2 && (
        <section className="pd6-card" aria-labelledby="pd-trend-title">
          <h3 id="pd-trend-title" className="pd6-section-title">Risk trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart margin={{ top: 10, right: 14, bottom: 0, left: 0 }} data={riskTrend.map(t => ({
              date: formatShortDatePH(t.created_at),
              score: t.risk_score,
              level: t.risk_level,
            }))}>
              {/* Colored severity bands stand in for the numeric axis, so the
                  chart still shows exactly where a point falls without ever
                  printing a raw score. */}
              <ReferenceArea y1={0} y2={35} fill={RISK_COLOR.LOW} fillOpacity={0.07} />
              <ReferenceArea y1={35} y2={70} fill={RISK_COLOR.MEDIUM} fillOpacity={0.07} />
              <ReferenceArea y1={70} y2={100} fill={RISK_COLOR.HIGH} fillOpacity={0.07} />
              <CartesianGrid strokeDasharray="3 3" stroke={T.border} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: T.muted }} />
              <YAxis
                domain={[0, 100]}
                ticks={[17, 52, 85]}
                tickFormatter={v => (v < 35 ? 'Low' : v < 70 ? 'Medium' : 'High')}
                tick={{ fontSize: 10, fill: T.muted }}
                width={52}
              />
              <Tooltip content={<RiskTrendTooltip />} />
              <Line type="monotone" dataKey="score" stroke={T.text} strokeWidth={2.5} dot={riskTrendDot} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}

      {!canViewClinical && (
        <EmptyState
          compact
          className="tw-state--card"
          icon={Lock}
          title="Clinical history is restricted"
          message="Screening results are visible to the dentist and the dental assistant."
        />
      )}

      {canViewClinical && (
        <section aria-labelledby="pd-history-title">
          <div className="pd6-section-head">
            <h3 id="pd-history-title" className="pd6-section-title">Screening history</h3>
            {!clinicalError && (
              <span className="pd6-count">{screenings.length} record{screenings.length !== 1 ? 's' : ''}</span>
            )}
          </div>

          {clinicalError ? (
            <EmptyState
              compact
              className="tw-state--card"
              role="alert"
              icon={CloudOff}
              title="Couldn't load screening history"
              message={clinicalError}
              action={<Button variant="secondary" size="sm" icon={RotateCw} onClick={load}>Try again</Button>}
            />
          ) : screenings.length === 0 ? (
            <EmptyState
              compact
              className="tw-state--card"
              icon={ScanSearch}
              title="No screenings yet"
              message="Run the first AI screening for this patient to begin their clinical history."
              action={<Button icon={ScanLine} onClick={startScreening}>Start First Screening</Button>}
            />
          ) : (
            <ul className="pd6-card pd6-history">
              {screenings.map(sc => {
                const count = sc.detection_count ?? 0;
                return (
                  <li key={sc.id}>
                    <button type="button" className="pd6-history-row" onClick={() => navigate('/dashboard/screenings/' + sc.id)}>
                      <span className="pd6-history-icon" aria-hidden="true"><ScanSearch size={18} /></span>
                      <span className="pd6-history-text">
                        <span className="pd6-history-title">Screening #{sc.id}</span>
                        <span className="pd6-history-meta">
                          {formatDatePH(sc.created_at)} · {count} detection{count !== 1 ? 's' : ''}
                        </span>
                      </span>
                      <RiskBadge level={sc.risk_level} size="sm" />
                      <span className="pd6-history-arrow" aria-hidden="true"><ArrowUpRight size={16} /></span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
