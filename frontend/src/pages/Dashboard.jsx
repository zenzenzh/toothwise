import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Microscope, Users, TriangleAlert, CalendarDays, UserPlus, ScanLine, ArrowRight, PieChart as PieIcon, CloudOff, RotateCw } from 'lucide-react';
import { dashboardAPI } from '../api';
import { SkeletonCard, SkeletonBlock } from '../components/Skeleton';
import PageHeader from '../components/ui/PageHeader';
import StatCard from '../components/ui/StatCard';
import EmptyState from '../components/ui/EmptyState';
import Button from '../components/ui/Button';
import T from '../tokens';

const PIE_COLORS = [T.accent, T.text, T.success, T.warning, T.indigo];

const TOOLTIP_STYLE = {
  background: T.surface,
  border: `1px solid ${T.border}`,
  borderRadius: 10,
  fontSize: 12,
  color: T.text,
};
const AXIS_TICK = { fontSize: 11, fill: T.muted };

const QUICK_ACTIONS = [
  { label: 'Register Patient', Icon: UserPlus, path: '/dashboard/patients', desc: 'Add a new patient record' },
  { label: 'Start Screening', Icon: ScanLine, path: '/dashboard/patients', desc: 'Run AI dental screening' },
];

function DashboardSkeleton() {
  return (
    <div className="dashboard-page tw-page-layout" aria-busy="true" aria-label="Loading dashboard">
      <div className="tw-page-header">
        <div>
          <SkeletonBlock width={220} height={26} />
          <SkeletonBlock width={180} height={13} style={{ marginTop: 10 }} />
        </div>
        <SkeletonBlock width={160} height={44} radius={10} />
      </div>
      <div className="dash6-stats-grid">
        {[0, 1, 2, 3].map(i => <SkeletonCard key={i} index={i} height={128} />)}
      </div>
      <div className="dash6-charts">
        <SkeletonCard index={4} height={290} />
        <SkeletonCard index={5} height={290} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = useCallback(() => {
    setError(null);
    setStats(null);
    dashboardAPI.stats()
      .then(r => setStats(r.data))
      .catch(err => setError(err.friendlyMessage || 'The dashboard could not be loaded.'));
  }, []);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="dashboard-page tw-page-layout">
        <EmptyState
          role="alert"
          icon={CloudOff}
          title="Couldn't load the overview"
          message={error}
          action={<Button variant="secondary" icon={RotateCw} onClick={load}>Try again</Button>}
        />
      </div>
    );
  }

  if (!stats) return <DashboardSkeleton />;

  const pieData = (stats.detection_breakdown || []).map(d => ({ name: d.label, value: d.count }));
  const today = new Date().toLocaleDateString('en-PH', { weekday: 'long', month: 'long', day: 'numeric' });

  const statItems = [
    { label: 'Total Screenings', value: stats.total_screenings, Icon: Microscope },
    { label: 'Total Patients', value: stats.total_patients, Icon: Users },
    { label: 'High Risk Cases', value: stats.high_risk_cases, Icon: TriangleAlert, danger: stats.high_risk_cases > 0 },
    { label: "Today's Screenings", value: stats.todays_screenings, Icon: CalendarDays },
  ];

  return (
    <div className="dashboard-page tw-page-layout">
      <PageHeader
        title="Overview"
        subtitle={today}
        actions={
          <Button icon={ScanLine} onClick={() => navigate('/dashboard/patients')}>
            New Screening
          </Button>
        }
      />

      <div className="dash6-stats-grid">
        {statItems.map(({ label, value, Icon, danger }, i) => (
          <StatCard
            key={label}
            className="stagger-item"
            style={{ '--stagger-index': i }}
            label={label}
            value={value ?? 0}
            icon={Icon}
            tone={danger ? 'danger' : 'default'}
          />
        ))}
      </div>

      <div className="dash6-charts">
        <section className="dash6-chart-card" aria-labelledby="dash-trend-title">
          <h3 id="dash-trend-title" className="dash6-chart-title">Monthly screening trend</h3>
          <p className="dash6-chart-sub">Last 6 months</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={stats.monthly_trend} barSize={28}>
              <defs>
                <linearGradient id="dash6-bar-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={T.text} />
                  <stop offset="100%" stopColor={T.accent} />
                </linearGradient>
              </defs>
              <XAxis dataKey="month" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} width={32} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: T.surfaceAlt }} />
              <Bar dataKey="count" name="Screenings" fill="url(#dash6-bar-grad)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="dash6-chart-card" aria-labelledby="dash-breakdown-title">
          <h3 id="dash-breakdown-title" className="dash6-chart-title">Detection breakdown</h3>
          <p className="dash6-chart-sub">By anomaly type</p>
          {pieData.length > 0 ? (
            <div className="dash6-pie">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                    innerRadius={52} outerRadius={84} paddingAngle={3} stroke="none">
                    {pieData.map((d, i) => (
                      <Cell key={d.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="dash6-legend">
                {pieData.map((d, i) => (
                  <li key={d.name}>
                    <span className="dash6-legend-dot" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="dash6-legend-label">{d.name}</span>
                    <span className="dash6-legend-value">{d.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState
              compact
              icon={PieIcon}
              title="No detections yet"
              message="Findings appear here once screenings are analysed."
            />
          )}
        </section>
      </div>

      <section aria-labelledby="dash-actions-title">
        <h3 id="dash-actions-title" className="dash6-section-title">Quick actions</h3>
        <div className="dash6-actions-grid">
          {QUICK_ACTIONS.map((a, i) => (
            <button
              key={a.label}
              type="button"
              className="dash6-action-card stagger-item"
              style={{ '--stagger-index': i }}
              onClick={() => navigate(a.path)}
            >
              <span className="dash6-action-icon" aria-hidden="true">
                <a.Icon size={20} strokeWidth={1.75} />
              </span>
              <span className="dash6-action-text">
                <span className="dash6-action-label">{a.label}</span>
                <span className="dash6-action-desc">{a.desc}</span>
              </span>
              <span className="dash6-action-arrow" aria-hidden="true"><ArrowRight size={18} strokeWidth={2} /></span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
