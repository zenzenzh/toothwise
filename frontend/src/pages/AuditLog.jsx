import { ShieldCheck } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { auditAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { formatDateTimePH } from '../utils/datetime';
import { SkeletonTableRows } from '../components/Skeleton';
import toast from 'react-hot-toast';

const BURGUNDY = '#4B2F35';
const MUTED = '#6F5B61';
const WHITE = '#FFFFFF';

const ACTION_COLOR = (action) => {
  if (action.includes('delete')) return '#C4505A';
  if (action.includes('create')) return '#2D7A52';
  if (action.includes('login.failed') || action.includes('rejected')) return '#D4850A';
  return '#4B2F35';
};

export default function AuditLog() {
  const { dentist: me } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    auditAPI.list({ action: actionFilter || undefined, limit: 200 })
      .then(r => setLogs(r.data))
      .catch(err => toast.error(err.friendlyMessage || 'Failed to load audit log'))
      .finally(() => setLoading(false));
  }, [actionFilter]);

  useEffect(() => {
    if (me?.role === 'admin') load();
  }, [me, load]);

  // Client-side gate for a clean, consistent UX (matches the Dentists
  // page). This is NOT the security boundary - the backend independently
  // rejects non-admin requests to /audit-logs regardless of what the UI
  // shows or hides here.
  if (me?.role !== 'admin') {
    return (
      <div style={s.forbidden}>
        <div style={s.forbiddenIcon}><ShieldCheck size={32} /></div>
        <h3 style={s.forbiddenTitle}>Admin Access Required</h3>
        <p style={s.forbiddenText}>Only administrators can view the audit log.</p>
      </div>
    );
  }

  return (
    <div className="tw-page-layout">
      <div className="tw-page-header">
        <div className="tw-page-title-wrap">
          <h2>Audit Log</h2>
          <p>System activity trail</p>
        </div>
        <select style={s.filterSelect} value={actionFilter} onChange={e => setActionFilter(e.target.value)}>
          <option value="">All actions</option>
          <option value="login.success">Login success</option>
          <option value="login.failed">Login failed</option>
          <option value="patient.create">Patient created</option>
          <option value="patient.update">Patient updated</option>
          <option value="patient.delete">Patient deleted</option>
          <option value="dentist.create">Dentist created</option>
          <option value="dentist.password_reset">Password reset</option>
          <option value="screening.create">Screening created</option>
          <option value="screening.delete">Screening deleted</option>
        </select>
      </div>

      {loading ? (
        <div className="audit6-table-card tw-responsive-table">
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>When</th>
                <th style={s.th}>Actor</th>
                <th style={s.th}>Action</th>
                <th style={s.th}>Entity</th>
                <th style={s.th}>Details</th>
              </tr>
            </thead>
            <tbody>
              <SkeletonTableRows columns={5} rows={7} />
            </tbody>
          </table>
        </div>
      ) : logs.length === 0 ? (
        <div style={s.emptyState}>
          <div style={s.emptyIcon}><ShieldCheck size={32} /></div>
          <h3 style={s.emptyTitle}>No entries</h3>
          <p style={s.emptyDesc}>No matching audit entries for the selected filter.</p>
        </div>
      ) : (
        <div className="audit6-table-card tw-responsive-table">
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>When</th>
                <th style={s.th}>Actor</th>
                <th style={s.th}>Action</th>
                <th style={s.th}>Entity</th>
                <th style={s.th}>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l, i) => (
                <tr key={l.id} className="stagger-item audit6-row" style={{ ...s.tr, '--stagger-index': i }}>
                  <td style={s.td} data-label="When">{formatDateTimePH(l.created_at)}</td>
                  <td style={s.td} data-label="Actor">{l.actor_email || 'system'}</td>
                  <td style={s.td} data-label="Action">
                    <span style={{ ...s.actionBadge, color: ACTION_COLOR(l.action), borderColor: ACTION_COLOR(l.action) }}>
                      {l.action}
                    </span>
                  </td>
                  <td style={s.td} data-label="Entity">{l.entity_type ? `${l.entity_type} #${l.entity_id}` : '—'}</td>
                  <td style={s.td} data-label="Details"><span style={s.detailsText}>{l.details || '—'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const s = {
  filterSelect: {
    background: WHITE, border: '1px solid #E5DADC', borderRadius: 11,
    padding: '10px 14px', fontSize: 13, color: BURGUNDY, fontFamily: 'inherit',
    minWidth: 220,
  },
  emptyState: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', padding: 80, gap: 16,
    background: WHITE, borderRadius: 18,
    border: '1px solid #E5DADC',
    boxShadow: '0 10px 30px rgba(75,47,53,0.05)',
  },
  emptyIcon: { fontSize: 48, color: MUTED },
  emptyTitle: { fontSize: 20, fontWeight: 700, color: BURGUNDY },
  emptyDesc: { fontSize: 13, color: MUTED },
  tableCard: {
    background: WHITE, borderRadius: 18,
    border: '1px solid #E5DADC',
    boxShadow: '0 10px 30px rgba(75,47,53,0.05)',
    overflow: 'hidden',
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    padding: '13px 18px', fontSize: 10.5, fontWeight: 700,
    color: MUTED, textTransform: 'uppercase', letterSpacing: '0.07em',
    borderBottom: '1px solid #E5DADC', textAlign: 'left',
    background: WHITE,
  },
  tr: { transition: 'background 0.12s ease' },
  td: { padding: '13px 18px', fontSize: 13, color: '#352126', borderBottom: '1px solid #F0E4E2' },
  actionBadge: {
    display: 'inline-block', border: '1px solid', borderRadius: 20,
    padding: '3px 10px', fontSize: 11, fontWeight: 700, fontFamily: 'monospace',
  },
  detailsText: { color: MUTED, fontSize: 12 },
  forbidden: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: 400, gap: 16,
  },
  forbiddenIcon: { fontSize: 48, color: MUTED },
  forbiddenTitle: { fontSize: 20, fontWeight: 700, color: BURGUNDY },
  forbiddenText: { fontSize: 14, color: MUTED, textAlign: 'center', maxWidth: 360 },
};