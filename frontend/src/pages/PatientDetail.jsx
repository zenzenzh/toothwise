import { useEffect, useState } from 'react';
import { ArrowLeft, ScanSearch, Plus, ArrowUpRight } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceArea } from 'recharts';
import { patientsAPI } from '../api';
import { formatDatePH, formatShortDatePH } from '../utils/datetime';
import { SkeletonBlock, SkeletonCircle, SkeletonCard } from '../components/Skeleton';
import toast from 'react-hot-toast';

const C = { burgundy: '#4B2F35', rose: '#BA7976', gold: '#C78C8A', blush: '#FBF7F5', white: '#FFFFFF', muted: '#6F5B61' };

const RISK_STYLE = {
  HIGH:   { background: '#FCE8EA', color: '#C4505A', border: '1px solid #F5C0C4' },
  MEDIUM: { background: '#FEF3E2', color: '#D4850A', border: '1px solid #F9DBA0' },
  LOW:    { background: '#E8F5EE', color: '#2D7A52', border: '1px solid #A8DBBE' },
};

// Trend chart shows severity level, never the raw internal score - the
// score still drives point height (so a genuine within-band change is
// still visible as movement), but nothing on screen prints a number.
function RiskTrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { date, level } = payload[0].payload;
  return (
    <div style={{ background: C.white, borderRadius: 8, border: `1px solid ${C.gold}`, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: C.muted, marginBottom: 3 }}>{date}</div>
      <span style={{ ...RISK_STYLE[level], padding: '2px 10px', borderRadius: 12, fontWeight: 700, fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {level}
      </span>
    </div>
  );
}

function riskTrendDot(props) {
  const { cx, cy, payload } = props;
  return <circle cx={cx} cy={cy} r={4} fill={RISK_STYLE[payload.level]?.color || C.rose} stroke={C.white} strokeWidth={1.5} />;
}

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [patient, setPatient] = useState(null);
  const [screenings, setScreenings] = useState([]);
  const [riskTrend, setRiskTrend] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([patientsAPI.get(id), patientsAPI.screenings(id), patientsAPI.riskTrend(id)])
      .then(([p, s, t]) => { setPatient(p.data); setScreenings(s.data); setRiskTrend(t.data); })
      .catch(err => toast.error(err.friendlyMessage || 'Failed to load patient'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <SkeletonCircle size={72} />
        <div style={{ flex: 1 }}>
          <SkeletonBlock width={200} height={22} />
          <div style={{ marginTop: 8 }}><SkeletonBlock width={140} height={13} /></div>
        </div>
      </div>
      <SkeletonCard index={0} height={150} />
      <SkeletonCard index={1} height={220} />
    </div>
  );

  if (!patient) return (
    <div className="patient-empty-view">
      <div className="patient-empty-icon"><ScanSearch size={28} /></div>
      <h3>Patient record not found</h3>
      <p>The patient may have been removed or you may no longer have access to this record.</p>
      <button className="tw-secondary-action-btn" onClick={() => navigate('/dashboard/patients')}>Back to Patients</button>
    </div>
  );

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
        <button className="tw-secondary-action-btn" onClick={() => navigate('/dashboard/patients')}><ArrowLeft size={15} /> Back to Patients</button>
        <button className="tw-primary-action-btn" onClick={() => navigate(`/dashboard/patients/${id}/screening`)}><Plus size={16} /> New Screening</button>
      </div>

      {/* Profile header: avatar + identity left, latest risk right */}
      <div style={s.profileCard} className="pd6-profile">
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, minWidth: 0, flexWrap: 'wrap' }}>
          <div style={BIG_AVATAR}>{patient.full_name.charAt(0)}</div>
          <div style={{ minWidth: 0 }}>
            <h2 style={{ fontSize: 23, fontWeight: 700, color: C.burgundy, margin: 0, letterSpacing: '-0.02em', wordBreak: 'break-word' }}>{patient.full_name}</h2>
            <p style={{ color: C.muted, fontSize: 12.5, marginTop: 4 }}>Patient ID #{patient.id}</p>
          </div>
        </div>
        {latestLevel && (
          <div style={s.profileRisk}>
            <span style={s.profileRiskLabel}>Latest result</span>
            <span style={{ ...RISK_STYLE[latestLevel], fontSize: 11.5, padding: '5px 14px', borderRadius: 20, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {latestLevel}
            </span>
          </div>
        )}
      </div>

      {/* Details as a ruled definition list, not tiles */}
      <div style={s.defsCard}>
        {details.map((item, i) => (
          <div key={i} className="pd6-def" style={s.defRow}>
            <span style={s.defLabel}>{item.label}</span>
            <span style={s.defValue}>{item.value}</span>
          </div>
        ))}
      </div>

      {riskTrend.length >= 2 && (
        <div style={s.card}>
          <h3 style={s.sectionHeading}>Risk trend</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={riskTrend.map(t => ({
              date: formatShortDatePH(t.created_at),
              score: t.risk_score,
              level: t.risk_level,
            }))}>
              {/* Colored severity bands stand in for the numeric axis, so the
                  chart still shows exactly where a point falls without ever
                  printing a raw score. */}
              <ReferenceArea y1={0} y2={35} fill={RISK_STYLE.LOW.color} fillOpacity={0.07} />
              <ReferenceArea y1={35} y2={70} fill={RISK_STYLE.MEDIUM.color} fillOpacity={0.07} />
              <ReferenceArea y1={70} y2={100} fill={RISK_STYLE.HIGH.color} fillOpacity={0.07} />
              <CartesianGrid strokeDasharray="3 3" stroke={C.blush} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: C.muted }} />
              <YAxis
                domain={[0, 100]}
                ticks={[17, 52, 85]}
                tickFormatter={v => (v < 35 ? 'Low' : v < 70 ? 'Medium' : 'High')}
                tick={{ fontSize: 10, fill: C.muted }}
                width={52}
              />
              <Tooltip content={<RiskTrendTooltip />} />
              <Line type="monotone" dataKey="score" stroke={C.burgundy} strokeWidth={2.5} dot={riskTrendDot} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10, flexWrap: 'wrap', gap: 6 }}>
          <h3 style={s.sectionHeading}>Screening history</h3>
          <span style={{ fontSize: 12, color: C.muted }}>
            {screenings.length} record{screenings.length !== 1 ? 's' : ''}
          </span>
        </div>

        {screenings.length === 0 ? (
          <div className="patient-empty-view compact">
            <div className="patient-empty-icon"><ScanSearch size={28} /></div>
            <h4>No screenings yet</h4>
            <p>Run the first AI screening for this patient to begin the clinical history.</p>
            <button className="tw-primary-action-btn" onClick={() => navigate(`/dashboard/patients/${id}/screening`)}>Start First Screening</button>
          </div>
        ) : (
          <div style={s.historyCard}>
            {screenings.map((sc, i) => {
              const level = sc.risk_level;
              return (
                <div key={sc.id}
                  className="pd6-history-row"
                  style={{ ...s.historyRow, ...(i === 0 ? { borderTop: 'none' } : {}) }}
                  onClick={() => navigate('/dashboard/screenings/' + sc.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => { if (e.key === 'Enter') navigate('/dashboard/screenings/' + sc.id); }}
                >
                  <div style={s.historyIcon}><ScanSearch size={18} /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: C.burgundy }}>Screening #{sc.id}</div>
                    <div style={{ fontSize: 11.5, color: C.muted, marginTop: 3 }}>
                      {formatDatePH(sc.created_at)}
                      {' · '}{sc.detection_count ?? 0} detection{(sc.detection_count ?? 0) !== 1 ? 's' : ''}
                    </div>
                  </div>
                  {level && (
                    <span style={{ ...RISK_STYLE[level], fontSize: 10.5, padding: '4px 13px', borderRadius: 20, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0 }}>
                      {level}
                    </span>
                  )}
                  <span style={s.historyArrow}><ArrowUpRight size={16} /></span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

const CARD = {
  background: C.white, borderRadius: 18, padding: '22px 24px',
  border: '1px solid #E5DADC', boxShadow: '0 10px 30px rgba(75,47,53,0.05)',
};
const BIG_AVATAR = { width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg, #BA7976, #C78C8A)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 28, flexShrink: 0 };

const s = {
  card: CARD,
  profileCard: {
    ...CARD,
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: 16, flexWrap: 'wrap', padding: '24px 26px',
  },
  profileRisk: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 },
  profileRiskLabel: { fontSize: 10, color: C.muted, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' },
  defsCard: { ...CARD, padding: '8px 24px' },
  defRow: {
    display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 18,
    padding: '13px 0', borderBottom: '1px solid #F0E4E2',
  },
  defLabel: { fontSize: 10.5, color: C.muted, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0 },
  defValue: { fontSize: 13.5, color: C.burgundy, fontWeight: 500, textAlign: 'right', overflowWrap: 'anywhere' },
  sectionHeading: { fontSize: 15.5, fontWeight: 700, color: C.burgundy, margin: 0, letterSpacing: '-0.01em' },
  historyCard: { ...CARD, padding: '4px 20px' },
  historyRow: {
    display: 'flex', alignItems: 'center', gap: 15,
    padding: '14px 2px', borderTop: '1px solid #F0E4E2',
    cursor: 'pointer', borderRadius: 8,
    transition: 'background 0.15s ease',
  },
  historyIcon: {
    width: 42, height: 42, borderRadius: 12, background: C.blush, color: C.rose,
    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    border: '1px solid #E5DADC',
  },
  historyArrow: { color: C.rose, flexShrink: 0, display: 'flex', alignItems: 'center' },
};
