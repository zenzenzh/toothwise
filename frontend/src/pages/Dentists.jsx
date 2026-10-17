import { useState, useEffect, useRef, useCallback } from 'react';
import { KeyRound, Trash2, CircleCheck, CircleOff, Pencil, UserCog, ArrowRight, UserPlus, SearchX, CloudOff, RotateCw, ShieldAlert } from 'lucide-react';
import { dentistsAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { isDentist, ROLE_LABELS } from '../utils/permissions';
import PasswordField from '../components/PasswordField';
import { validateEmail, validatePassword, validateRequiredText, validateOptionalText, LIMITS } from '../utils/validation';
import { SkeletonTableRows } from '../components/Skeleton';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import FormField from '../components/ui/FormField';
import SearchField from '../components/ui/SearchField';
import toast from 'react-hot-toast';

const EMPTY_FORM = {
  first_name: '', middle_name: '', last_name: '', email: '', password: '', role: 'receptionist', license_no: ''
};

const COLUMNS = ['Name', 'Role', 'License No.', 'Status', 'Actions'];

// Role pill tones: dentist/administrator, receptionist, assistant.
const ROLE_TONE = { dentist: 'accent', receptionist: 'warning', assistant: 'success' };

// Form order, so validation focuses the first invalid field.
const FIELD_IDS = [
  ['first_name', 'st-first-name'],
  ['middle_name', 'st-middle-name'],
  ['last_name', 'st-last-name'],
  ['email', 'st-email'],
];

function StaffTable({ children }) {
  return (
    <div className="tw-table-card tw-responsive-table">
      <table className="tw-data-table tw-data-table--static">
        <thead>
          <tr>{COLUMNS.map(c => <th key={c} scope="col" className={c === 'License No.' ? 'tw-col-optional' : undefined}>{c}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export default function Dentists() {
  const { dentist: me } = useAuth();
  const [dentists, setDentists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showPwModal, setShowPwModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [pwForm, setPwForm] = useState({ new_password: '', confirm: '' });
  const [pwTarget, setPwTarget] = useState(null);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [formErrors, setFormErrors] = useState({});
  const [pwErrors, setPwErrors] = useState({});
  const [confirm, setConfirm] = useState(null); // { type: 'delete' | 'deactivate', staff }
  const [confirmBusy, setConfirmBusy] = useState(false);
  const [togglingId, setTogglingId] = useState(null);
  const searchRef = useRef(null);
  const allowed = isDentist(me?.role);

  const load = useCallback(() => {
    setLoading(true);
    setLoadError(null);
    dentistsAPI.list()
      .then(r => setDentists(r.data))
      .catch(err => setLoadError(err.friendlyMessage || 'Staff accounts could not be loaded.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  function setField(name, value) {
    setForm(f => ({ ...f, [name]: value }));
    if (formErrors[name]) setFormErrors(f => ({ ...f, [name]: undefined }));
  }

  function openAdd() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(d) {
    setEditing(d);
    setForm({
      first_name: d.first_name || '',
      middle_name: d.middle_name || '',
      last_name: d.last_name || '',
      email: d.email,
      password: '',
      role: d.role,
      license_no: d.license_no || ''
    });
    setFormErrors({});
    setShowModal(true);
  }

  function openPw(d) {
    setPwTarget(d);
    setPwForm({ new_password: '', confirm: '' });
    setPwErrors({});
    setShowPwModal(true);
  }

  async function handleSave(e) {
    e.preventDefault();

    const firstCheck = validateRequiredText(form.first_name, 'First name');
    const lastCheck = validateRequiredText(form.last_name, 'Last name');
    const middleCheck = validateOptionalText(form.middle_name, 'Middle name', LIMITS.NAME_MAX);
    const emailCheck = validateEmail(form.email);
    const nextErrors = {};
    if (!firstCheck.valid) nextErrors.first_name = firstCheck.message;
    if (!lastCheck.valid) nextErrors.last_name = lastCheck.message;
    if (!middleCheck.valid) nextErrors.middle_name = middleCheck.message;
    if (!emailCheck.valid) nextErrors.email = emailCheck.message;
    if (!editing) {
      const passwordCheck = validatePassword(form.password);
      if (!passwordCheck.valid) nextErrors.password = passwordCheck.message;
    }
    if (Object.keys(nextErrors).length > 0) {
      setFormErrors(nextErrors);
      const firstInvalid = FIELD_IDS.find(([name]) => nextErrors[name]);
      if (firstInvalid) document.getElementById(firstInvalid[1])?.focus();
      return;
    }
    setFormErrors({});

    setSaving(true);
    try {
      if (editing) {
        await dentistsAPI.update(editing.id, {
          first_name: firstCheck.value,
          middle_name: middleCheck.value || null,
          last_name: lastCheck.value,
          email: emailCheck.value,
          role: form.role,
          license_no: form.license_no,
        });
        toast.success('Staff member updated');
      } else {
        await dentistsAPI.create({
          first_name: firstCheck.value,
          middle_name: middleCheck.value || null,
          last_name: lastCheck.value,
          email: emailCheck.value,
          password: form.password,
          role: form.role,
          license_no: form.license_no,
        });
        toast.success('Staff member added');
      }
      setShowModal(false);
      load();
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function setActive(d, isActive) {
    setTogglingId(d.id);
    try {
      await dentistsAPI.update(d.id, { is_active: isActive });
      toast.success(isActive ? `${d.full_name} activated` : `${d.full_name} deactivated`);
      load();
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to update status');
    } finally {
      setTogglingId(null);
    }
  }

  async function runConfirm() {
    if (!confirm) return;
    const { type, staff } = confirm;
    setConfirmBusy(true);
    try {
      if (type === 'delete') {
        await dentistsAPI.delete(staff.id);
        toast.success(`${staff.full_name} deleted`);
        load();
      } else {
        await setActive(staff, false);
      }
      setConfirm(null);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to delete');
    } finally {
      setConfirmBusy(false);
    }
  }

  async function handlePwSave(e) {
    e.preventDefault();
    const passwordCheck = validatePassword(pwForm.new_password);
    const nextErrors = {};
    if (!passwordCheck.valid) nextErrors.new_password = passwordCheck.message;
    else if (pwForm.new_password !== pwForm.confirm) nextErrors.confirm = 'Passwords do not match.';
    if (Object.keys(nextErrors).length > 0) {
      setPwErrors(nextErrors);
      return;
    }
    setPwErrors({});
    setSaving(true);
    try {
      await dentistsAPI.resetPassword(pwTarget.id, pwForm.new_password);
      toast.success('Password updated');
      setShowPwModal(false);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to update password');
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) {
    return (
      <div className="tw-page-layout">
        <EmptyState
          className="tw-state--card"
          icon={ShieldAlert}
          title="Dentist access required"
          message="Only the dentist (administrator) can manage staff accounts."
        />
      </div>
    );
  }

  const q = search.trim().toLowerCase();
  const filtered = q
    ? dentists.filter(d => d.full_name.toLowerCase().includes(q) || d.email.toLowerCase().includes(q))
    : dentists;
  const activeCount = dentists.filter(d => d.is_active).length;

  const subtitle = loadError
    ? undefined
    : loading && dentists.length === 0
      ? 'Loading accounts…'
      : q
        ? `${filtered.length} of ${dentists.length} members`
        : `${dentists.length} ${dentists.length === 1 ? 'member' : 'members'} · ${activeCount} active`;

  let body;
  if (loadError) {
    body = (
      <EmptyState
        className="tw-state--card"
        role="alert"
        icon={CloudOff}
        title="Couldn't load staff"
        message={loadError}
        action={<Button variant="secondary" icon={RotateCw} onClick={load}>Try again</Button>}
      />
    );
  } else if (loading && dentists.length === 0) {
    body = <StaffTable><SkeletonTableRows columns={5} rows={5} /></StaffTable>;
  } else if (filtered.length === 0 && q) {
    body = (
      <EmptyState
        className="tw-state--card"
        icon={SearchX}
        title="No matching staff"
        message={`Nobody matches “${search.trim()}”. Try a name or email address.`}
        action={<Button variant="secondary" onClick={() => { setSearch(''); searchRef.current?.focus(); }}>Clear search</Button>}
      />
    );
  } else if (filtered.length === 0) {
    body = (
      <EmptyState
        className="tw-state--card"
        icon={UserCog}
        title="No staff members yet"
        message="Add the first staff member to get started."
        action={<Button icon={UserPlus} onClick={openAdd}>Add Staff Member</Button>}
      />
    );
  } else {
    body = (
      <StaffTable>
        {filtered.map((d, i) => {
          const isMe = d.id === me?.id;
          return (
            <tr key={d.id} className="stagger-item staff6-row" style={{ '--stagger-index': i }}>
              <td data-label="Name">
                <div className="tw-person">
                  <div className={`tw-avatar ${d.is_active ? '' : 'tw-avatar--muted'}`.trim()} aria-hidden="true">{d.full_name.charAt(0)}</div>
                  <div className="tw-person__text">
                    <div className="tw-person__name">
                      {d.full_name}
                      {isMe && <Badge tone="info" className="tw-person__tag">You</Badge>}
                    </div>
                    <div className="tw-person__meta" title={d.email}>{d.email}</div>
                  </div>
                </div>
              </td>
              <td data-label="Role"><Badge tone={ROLE_TONE[d.role] || 'neutral'}>{ROLE_LABELS[d.role] || d.role}</Badge></td>
              <td data-label="License No." className="tw-col-optional">{d.license_no || '—'}</td>
              <td data-label="Status">
                <Badge tone={d.is_active ? 'success' : 'neutral'} dot>{d.is_active ? 'Active' : 'Inactive'}</Badge>
              </td>
              <td data-label="Actions">
                <div className="tw-row-actions">
                  <button type="button" className="tw-row-btn tw-row-btn--icon" onClick={() => openEdit(d)} title="Edit" aria-label={`Edit ${d.full_name}`}>
                    <Pencil size={15} aria-hidden="true" />
                  </button>
                  <button type="button" className="tw-row-btn tw-row-btn--icon" onClick={() => openPw(d)} title="Reset password" aria-label={`Reset password for ${d.full_name}`}>
                    <KeyRound size={15} aria-hidden="true" />
                  </button>
                  {!isMe && (
                    <>
                      <button
                        type="button"
                        className="tw-row-btn tw-row-btn--icon"
                        onClick={() => (d.is_active ? setConfirm({ type: 'deactivate', staff: d }) : setActive(d, true))}
                        disabled={togglingId === d.id}
                        title={d.is_active ? 'Deactivate' : 'Activate'}
                        aria-label={`${d.is_active ? 'Deactivate' : 'Activate'} ${d.full_name}`}
                      >
                        {d.is_active ? <CircleOff size={15} aria-hidden="true" /> : <CircleCheck size={15} aria-hidden="true" />}
                      </button>
                      <button
                        type="button"
                        className="tw-row-btn tw-row-btn--icon tw-row-btn--danger"
                        onClick={() => setConfirm({ type: 'delete', staff: d })}
                        title="Delete"
                        aria-label={`Delete ${d.full_name}`}
                      >
                        <Trash2 size={15} aria-hidden="true" />
                      </button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          );
        })}
      </StaffTable>
    );
  }

  const confirmStaff = confirm?.staff;

  return (
    <div className="tw-page-layout">
      <PageHeader
        title="Staff"
        subtitle={subtitle}
        actions={<Button icon={UserPlus} onClick={openAdd}>Add Staff Member</Button>}
      />

      <SearchField
        id="staff-search"
        ref={searchRef}
        label="Search staff by name or email"
        placeholder="Search by name or email…"
        value={search}
        onChange={setSearch}
      />

      <div aria-live="polite" aria-busy={loading}>{body}</div>

      <Modal
        isOpen={showModal}
        onClose={() => { if (!saving) setShowModal(false); }}
        title={editing ? 'Edit staff member' : 'Add a staff member'}
        icon={UserCog}
        dismissible={!saving}
      >
        <form onSubmit={handleSave} className="tw6-modal-form" noValidate>
          <div className="tw6-modal-section">
            <div className="tw6-modal-grid tw6-modal-grid-3">
              <FormField id="st-first-name" label="First name" required error={formErrors.first_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.first_name} onChange={e => setField('first_name', e.target.value)} placeholder="Juan" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
              <FormField id="st-middle-name" label="Middle name / initial" error={formErrors.middle_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.middle_name} onChange={e => setField('middle_name', e.target.value)} placeholder="Santos" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
              <FormField id="st-last-name" label="Last name" required error={formErrors.last_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.last_name} onChange={e => setField('last_name', e.target.value)} placeholder="Dela Cruz" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
            </div>
          </div>
          <div className="tw6-modal-section">
            <FormField id="st-email" label="Email" required error={formErrors.email}>
              {a => <input {...a} className="tw6-modal-input" type="email" value={form.email} onChange={e => setField('email', e.target.value)} placeholder="staff@codismile.com" maxLength={LIMITS.EMAIL_MAX} autoComplete="off" />}
            </FormField>
          </div>
          {!editing && (
            <div className="tw6-modal-section">
              <PasswordField
                value={form.password}
                onChange={v => setField('password', v)}
                label="Password *"
                showRequirements
                error={formErrors.password}
                inputClassName="tw6-modal-input tw6-modal-input-password"
                labelClassName="tw6-modal-label"
                fieldClassName="tw6-modal-field"
              />
            </div>
          )}
          <div className="tw6-modal-section">
            <div className="tw6-modal-grid tw6-modal-grid-2">
              <FormField id="st-role" label="Role" required hint={form.role === 'dentist' ? 'Administrators can manage staff and view the audit trail.' : undefined}>
                {a => (
                  <select {...a} className="tw6-modal-input" value={form.role} onChange={e => setField('role', e.target.value)}>
                    <option value="dentist">Dentist (administrator)</option>
                    <option value="receptionist">Receptionist</option>
                    <option value="assistant">Assistant</option>
                  </select>
                )}
              </FormField>
              <FormField id="st-license" label="PRC license no.">
                {a => <input {...a} className="tw6-modal-input" value={form.license_no} onChange={e => setField('license_no', e.target.value)} placeholder="PRC-12345" autoComplete="off" />}
              </FormField>
            </div>
          </div>
          <div className="tw6-modal-footer">
            <button type="button" className="tw6-modal-cancel" onClick={() => setShowModal(false)} disabled={saving}>Cancel</button>
            <button type="submit" className="tw6-modal-save" disabled={saving} aria-busy={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Add staff member'}
              {!saving && <ArrowRight size={15} aria-hidden="true" />}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showPwModal}
        onClose={() => { if (!saving) setShowPwModal(false); }}
        title="Reset password"
        icon={KeyRound}
        className="tw6-modal-compact"
        dismissible={!saving}
      >
        <div className="tw6-modal-target">
          <div className="tw6-modal-target-mark" aria-hidden="true">{pwTarget?.full_name?.charAt(0)?.toUpperCase() || 'S'}</div>
          <div className="tw6-modal-target-text">
            <strong>{pwTarget?.full_name}</strong>
            <span>{pwTarget?.email}</span>
          </div>
        </div>
        <form onSubmit={handlePwSave} className="tw6-modal-form" noValidate>
          <PasswordField value={pwForm.new_password} onChange={v => { setPwForm(f => ({ ...f, new_password: v })); if (pwErrors.new_password) setPwErrors(x => ({ ...x, new_password: undefined })); }} label="New password *" showRequirements error={pwErrors.new_password} inputClassName="tw6-modal-input tw6-modal-input-password" labelClassName="tw6-modal-label" fieldClassName="tw6-modal-field" />
          <PasswordField value={pwForm.confirm} onChange={v => { setPwForm(f => ({ ...f, confirm: v })); if (pwErrors.confirm) setPwErrors(x => ({ ...x, confirm: undefined })); }} label="Confirm password *" placeholder="Repeat password" error={pwErrors.confirm} inputClassName="tw6-modal-input tw6-modal-input-password" labelClassName="tw6-modal-label" fieldClassName="tw6-modal-field" />
          <div className="tw6-modal-footer">
            <button type="button" className="tw6-modal-cancel" onClick={() => setShowPwModal(false)} disabled={saving}>Cancel</button>
            <button type="submit" className="tw6-modal-save" disabled={saving} aria-busy={saving}>
              {saving ? 'Updating…' : 'Update password'}
              {!saving && <ArrowRight size={15} aria-hidden="true" />}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!confirm}
        onCancel={() => { if (!confirmBusy) setConfirm(null); }}
        onConfirm={runConfirm}
        busy={confirmBusy}
        title={confirm?.type === 'delete' ? 'Delete staff account?' : 'Deactivate account?'}
        message={confirmStaff ? (
          confirm.type === 'delete' ? (
            <><strong>{confirmStaff.full_name}</strong> will be permanently removed and can no longer sign in. This can't be undone.</>
          ) : (
            <><strong>{confirmStaff.full_name}</strong> won't be able to sign in until the account is activated again.</>
          )
        ) : ''}
        confirmText={confirm?.type === 'delete' ? 'Delete account' : 'Deactivate'}
      />
    </div>
  );
}
