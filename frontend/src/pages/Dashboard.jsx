import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Microscope, Users, TriangleAlert, CalendarDays, UserPlus, ScanLine, ArrowRight } from 'lucide-react';
import { dashboardAPI } from '../api';
import { SkeletonCard, SkeletonBlock } from '../components/Skeleton';
import toast from 'react-hot-toast';
import T from '../tokens';

const { burgundy: BURGUNDY, rose: ROSE, white: WHITE, muted: MUTED } = T;
const PIE_COLORS = [T.rose, T.burgundy, T.success];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardAPI.stats()
      .then(r => setStats(r.data))
      .catch(err => toast.error(err.friendlyMessage || 'Failed to load dashboard'));
  }, []);

  if (!stats) return (
    <div className="dashboard-page" style={s.page}>
      <div style={s.header}>
        <div>
          <SkeletonBlock width={220} height={26} />
          <div style={{ marginTop: 10 }}><SkeletonBlock width={320} height={13} /></div>
        </div>
        <SkeletonBlock width={160} height={44} radius={10} />
      </div>
      <SkeletonCard index={0} height={140} />
      <div style={s.charts}>
        <SkeletonCard index={1} height={280} />
        <SkeletonCard index={2} height={280} />
      </div>
    </div>
  );

  const pieData = (stats.detection_breakdown || []).map(d => ({ name: d.label, value: d.count }));
  const today = new Date().toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' });

  const secondary = [
    { label: 'Total Patients', value: stats.total_patients, Icon: Users },
    { label: 'High Risk Cases', value: stats.high_risk_cases, Icon: TriangleAlert, danger: stats.high_risk_cases > 0 },
    { label: "Today's Screenings", value: stats.todays_screenings, Icon: CalendarDays },
  ];

  return (
    <div className="dashboard-page tw-page-layout">
      <div className="tw-page-header">
        <div className="tw-page-title-wrap">
          <h2>Overview</h2>
          <p>{today}</p>
        </div>
        <button className="tw-primary-action-btn" onClick={() => navigate('/dashboard/patients')}>
          + New Screening
        </button>
      </div>

      {/* Stats grid: 4 equal cards in a row */}
      <div style={s.statsGrid} className="stagger-item">
        {[
          { label: 'Total Screenings', value: stats.total_screenings, Icon: Microscope, accent: false },
          ...secondary,
        ].map(({ label, value, Icon, danger }, i) => (
          <div key={label} className="dash6-stat-card" style={{ ...s.statCard, '--stagger-index': i }}>
            <div style={{ ...s.statIconWrap, ...(danger ? s.statIconDanger : {}) }}>
                  <Icon size={20} strokeWidth={1.75} color={danger ? T.danger : BURGUNDY} />
            </div>
            <div style={s.statValue}>{value}</div>
            <div style={s.statLabel}>{label}</div>
          </div>
        ))}
      </div>

      {/* Charts side by side */}
      <div className="dash6-charts" style={s.chartsRow}>
        <div style={s.chartCard}>
          <div style={s.chartHeader}>
            <div>
              <h3 style={s.chartTitle}>Monthly screening trend</h3>
              <p style={s.chartSub}>Last 6 months</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.monthly_trend} barSize={28}>
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: MUTED }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: MUTED }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: WHITE, border: `1px solid ${T.border}`, borderRadius: 10, fontSize: 12 }}
                cursor={{ fill: 'rgba(196,132,126,0.08)' }}
              />
              <Bar dataKey="count" fill="url(#dash6-bar-grad)" radius={[6, 6, 0, 0]} />
              <defs>
                <linearGradient id="dash6-bar-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={BURGUNDY} />
                  <stop offset="100%" stopColor={ROSE} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={s.chartCard}>
          <div style={s.chartHeader}>
            <div>
              <h3 style={s.chartTitle}>Detection breakdown</h3>
              <p style={s.chartSub}>By anomaly type</p>
            </div>
          </div>
          {pieData.length > 0 ? (
            <div style={s.pieWrap}>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    innerRadius={50} outerRadius={80} paddingAngle={4}>
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                   <Tooltip contentStyle={{ background: WHITE, border: `1px solid ${T.border}`, borderRadius: 10, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div style={s.legend}>
                {pieData.map((d, i) => (
                  <div key={i} style={s.legendItem}>
                    <div style={{ ...s.legendDot, background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span style={s.legendLabel}>{d.name}</span>
                    <span style={s.legendVal}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={s.empty}>No detection data yet</div>
          )}
        </div>
      </div>

      {/* Quick actions: modern card grid */}
      <div style={s.actionsSection}>
        <h3 style={s.actTitle}>Quick actions</h3>
        <div className="dash6-actions-grid" style={s.actionsGrid}>
          {[
            { label: 'Register Patient', Icon: UserPlus, path: '/dashboard/patients', desc: 'Add a new patient record' },
            { label: 'Start Screening', Icon: ScanLine, path: '/dashboard/patients', desc: 'Run AI dental screening' },
          ].map((a, i) => (
            <div
              key={i}
              className="dash6-action-card stagger-item"
              style={{ '--stagger-index': i }}
              onClick={() => navigate(a.path)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') navigate(a.path); }}
            >
              <div className="dash6-action-icon">
                <a.Icon size={20} strokeWidth={1.75} color={BURGUNDY} />
              </div>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={s.actLabel}>{a.label}</div>
                <div style={s.actDesc}>{a.desc}</div>
              </div>
              <span style={s.actArrow}><ArrowRight size={18} strokeWidth={2} /></span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const s = {
  statsGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20,
  },
  statCard: {
    background: WHITE, borderRadius: 16, padding: '20px',
    border: `1px solid ${T.border}`,
    boxShadow: '0 4px 20px rgba(0,0,0,.06)',
    display: 'flex', flexDirection: 'column', gap: 8,
  },
  statIconWrap: {
    width: 42, height: 42, borderRadius: 12,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: T.blush, border: `1px solid ${T.border}`,
  },
  statIconDanger: { background: T.dangerBg, border: `1px solid ${T.dangerBorder}` },
  statValue: { fontSize: 32, fontWeight: 700, lineHeight: 1, color: BURGUNDY, letterSpacing: '-0.02em' },
  statLabel: { fontSize: 12, color: MUTED, fontWeight: 600 },

  chartsRow: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 20 },
  chartCard: {
    background: WHITE, borderRadius: 18, padding: '22px 24px',
    border: `1px solid ${T.border}`,
    boxShadow: '0 4px 20px rgba(0,0,0,.05)',
  },
  chartHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  chartTitle: { fontSize: 15, fontWeight: 700, color: BURGUNDY, margin: 0, letterSpacing: '-0.01em' },
  chartSub: { fontSize: 12, color: MUTED, marginTop: 3, marginBottom: 0 },
  pieWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center' },
  legend: { display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12, width: '100%' },
  legendItem: { display: 'flex', alignItems: 'center', gap: 8 },
  legendDot: { width: 9, height: 9, borderRadius: '50%', flexShrink: 0 },
  legendLabel: { fontSize: 12, color: MUTED, flex: 1, textTransform: 'capitalize' },
  legendVal: { fontSize: 13, fontWeight: 600, color: BURGUNDY },
  empty: { textAlign: 'center', color: MUTED, padding: '40px 0', fontSize: 13 },

  actionsSection: { marginTop: 4 },
  actionsGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 },
  actTitle: { fontSize: 15, fontWeight: 700, color: BURGUNDY, margin: '0 0 12px' },
  actLabel: { fontSize: 14.5, fontWeight: 600, color: BURGUNDY },
  actDesc: { fontSize: 12, color: MUTED, marginTop: 2 },
  actArrow: { marginLeft: 'auto', color: ROSE, flexShrink: 0, display: 'flex', alignItems: 'center' },
};
