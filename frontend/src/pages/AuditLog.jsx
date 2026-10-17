import { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, CloudOff, RotateCw, ListFilter } from 'lucide-react';
import { auditAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { isDentist } from '../utils/permissions';
import { formatDateTimePH } from '../utils/datetime';
import { SkeletonTableRows } from '../components/Skeleton';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import SearchField from '../components/ui/SearchField';

const LIMIT = 200;
const COLUMNS = ['When', 'Actor', 'Action', 'Entity', 'Details'];

// Every action the backend writes (backend/app/routers), grouped for the filter.
const ACTION_GROUPS = [
  { label: 'Sign-in', actions: [
    ['login.success', 'Login succeeded'],
    ['login.failed', 'Login failed'],
    ['login.rejected_inactive', 'Login rejected (inactive)'],
  ] },
  { label: 'Patients', actions: [
    ['patient.create', 'Patient created'],
    ['patient.self_register', 'Patient self-registered'],
    ['patient.update', 'Patient updated'],
    ['patient.delete', 'Patient deleted'],
  ] },
  { label: 'Screenings', actions: [
    ['screening.create', 'Screening created'],
    ['screening.tier_confirm', 'Screening tier confirmed'],
    ['screening.report_pdf', 'PDF report exported'],
    ['screening.delete', 'Screening deleted'],
  ] },
  { label: 'Staff', actions: [
    ['dentist.create', 'Staff created'],
    ['dentist.update', 'Staff updated'],
    ['dentist.activate', 'Staff activated'],
    ['dentist.deactivate', 'Staff deactivated'],
    ['dentist.password_reset', 'Password reset'],
    ['dentist.delete', 'Staff deleted'],
  ] },
  { label: 'Assistant', actions: [
    ['toothwise.chatbot', 'Chatbot used'],
  ] },
];
const ACTION_LABELS = Object.fromEntries(ACTION_GROUPS.flatMap(g => g.actions));

function actionTone(action) {
  if (action.includes('delete') || action.includes('deactivate')) return 'danger';
  if (action.includes('failed') || action.includes('rejected') || action.includes('password_reset')) return 'warning';
  if (action.includes('create') || action.includes('register') || action.includes('activate')) return 'success';
  return 'neutral';
}

function AuditTable({ children }) {
  return (
    <div className="tw-table-card tw-responsive-table">
      <table className="tw-data-table tw-data-table--static">
        <thead>
          <tr>{COLUMNS.map(c => <th key={c} scope="col" className={c === 'Entity' ? 'tw-col-optional' : undefined}>{c}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export default function AuditLog() {
  const { dentist: me } = useAuth();
  const allowed = isDentist(me?.role);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionFilter, setActionFilter] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    auditAPI.list({ action: actionFilter || undefined, limit: LIMIT })
      .then(r => setLogs(r.data))
      .catch(err => setLoadError(err.friendlyMessage || 'The audit log could not be loaded.'))
      .finally(() => setLoading(false));
  }, [actionFilter]);

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  // Client-side gate for a clean, consistent UX (matches the Staff
  // page). This is NOT the security boundary - the backend independently
  // rejects non-dentist requests to /audit-logs regardless of what the UI
  // shows or hides here.
  if (!allowed) {
    return (
      <div className="tw-page-layout">
        <EmptyState
          className="tw-state--card"
          icon={ShieldAlert}
          title="Dentist access required"
          message="Only the dentist (administrator) can view the audit log."
        />
      </div>
    );
  }

  const q = search.trim().toLowerCase();
  const visible = q
    ? logs.filter(l => [l.actor_email, l.details, l.entity_type, l.action, ACTION_LABELS[l.action]]
        .some(v => v && String(v).toLowerCase().includes(q)))
    : logs;

  const subtitle = loadError
    ? 'System activity trail'
    : loading && logs.length === 0
      ? 'Loading activity…'
      : `${q ? `${visible.length} of ` : ''}${logs.length} ${logs.length === 1 ? 'entry' : 'entries'}${logs.length >= LIMIT ? ` (latest ${LIMIT})` : ''}`;

  let body;
  if (loadError) {
    body = (
      <EmptyState
        className="tw-state--card"
        role="alert"
        icon={CloudOff}
        title="Couldn't load the audit log"
        message={loadError}
        action={<Button variant="secondary" icon={RotateCw} onClick={load}>Try again</Button>}
      />
    );
  } else if (loading && logs.length === 0) {
    body = <AuditTable><SkeletonTableRows columns={5} rows={7} /></AuditTable>;
  } else if (visible.length === 0) {
    const filtered = actionFilter || q;
    body = (
      <EmptyState
        className="tw-state--card"
        icon={filtered ? ListFilter : ShieldCheck}
        title={filtered ? 'No matching entries' : 'No activity yet'}
        message={filtered ? 'Nothing matches the current filter or search.' : 'Actions such as sign-ins and record changes will appear here.'}
        action={filtered ? <Button variant="secondary" onClick={() => { setActionFilter(''); setSearch(''); }}>Clear filters</Button> : undefined}
      />
    );
  } else {
    body = (
      <AuditTable>
        {visible.map((l, i) => (
          <tr key={l.id} className="stagger-item audit6-row" style={{ '--stagger-index': Math.min(i, 20) }}>
            <td data-label="When"><time dateTime={l.created_at} className="audit6-when">{formatDateTimePH(l.created_at)}</time></td>
            <td data-label="Actor"><span className="tw-cell-clip" title={l.actor_email || 'system'}>{l.actor_email || 'system'}</span></td>
            <td data-label="Action">
              <span className={`tw-pill tw-pill--${actionTone(l.action)}`} title={l.action}>
                {ACTION_LABELS[l.action] || l.action}
              </span>
            </td>
            <td data-label="Entity" className="tw-col-optional">{l.entity_type ? `${l.entity_type} #${l.entity_id}` : '—'}</td>
            <td data-label="Details"><span className="audit6-details" title={l.details || undefined}>{l.details || '—'}</span></td>
          </tr>
        ))}
      </AuditTable>
    );
  }

  return (
    <div className="tw-page-layout">
      <PageHeader
        title="Audit Log"
        subtitle={subtitle}
        actions={
          <div className="audit6-filter">
            <label htmlFor="audit-action" className="sr-only">Filter by action</label>
            <ListFilter size={15} className="audit6-filter-icon" aria-hidden="true" />
            <select id="audit-action" className="audit6-select" value={actionFilter} onChange={e => setActionFilter(e.target.value)}>
              <option value="">All actions</option>
              {ACTION_GROUPS.map(g => (
                <optgroup key={g.label} label={g.label}>
                  {g.actions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </optgroup>
              ))}
            </select>
          </div>
        }
      />

      <SearchField
        id="audit-search"
        label="Search the audit log"
        placeholder="Search by actor, action or details…"
        value={search}
        onChange={setSearch}
      />

      <div aria-live="polite" aria-busy={loading}>{body}</div>
    </div>
  );
}
