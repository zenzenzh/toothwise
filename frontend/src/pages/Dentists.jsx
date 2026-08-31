import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { KeyRound, Trash2, CircleCheck, CircleOff, Pencil, X, UserCog, ArrowRight } from 'lucide-react';
import { dentistsAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import PasswordField from '../components/PasswordField';
import { validateEmail, validatePassword, validateRequiredText, validateOptionalText, LIMITS } from '../utils/validation';
import { SkeletonTableRows } from '../components/Skeleton';
import toast from 'react-hot-toast';

const BURGUNDY = '#4B2F35';
const ROSE = '#BA7976';
const ROSEGOLD = '#C78C8A';
const BLUSH = '#FBF7F5';
const WHITE = '#FFFFFF';
const MUTED = '#6F5B61';

const EMPTY_FORM = {
  first_name: '', middle_name: '', last_name: '', email: '', password: '', role: 'dentist', license_no: ''
};

export default function Dentists() {
  const { dentist: me } = useAuth();
  const [dentists, setDentists] = useState([]);
  const [loading, setLoading] = useState(true);
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

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!showModal && !showPwModal) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') { setShowModal(false); setShowPwModal(false); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [showModal, showPwModal]);

  function load() {
    setLoading(true);
    dentistsAPI.list()
      .then(r => setDentists(r.data))
      .catch(() => toast.error('Failed to load dentists'))
      .finally(() => setLoading(false));
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
      return;
    }
    setFormErrors({});

    setSaving(true);
    try {
      if (editing) {
        const update = {
          first_name: firstCheck.value,
          middle_name: middleCheck.value || null,
          last_name: lastCheck.value,
          email: emailCheck.value,
          role: form.role,
          license_no: form.license_no,
        };
        await dentistsAPI.update(editing.id, update);
        toast.success('Dentist updated!');
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
        toast.success('Dentist added!');
      }
      setShowModal(false);
      load();
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(d) {
    if (!window.confirm(`Delete ${d.full_name}? This cannot be undone.`)) return;
    try {
      await dentistsAPI.delete(d.id);
      toast.success('Dentist deleted');
      load();
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to delete');
    }
  }

  async function handleToggleActive(d) {
    try {
      await dentistsAPI.update(d.id, { is_active: !d.is_active });
      toast.success(d.is_active ? 'Account deactivated' : 'Account activated');
      load();
    } catch {
      toast.error('Failed to update status');
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
      toast.success('Password updated!');
      setShowPwModal(false);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to update password');
    } finally {
      setSaving(false);
    }
  }

  const filtered = dentists.filter(d =>
    d.full_name.toLowerCase().includes(search.toLowerCase()) ||
    d.email.toLowerCase().includes(search.toLowerCase())
  );

  if (me?.role !== 'admin') {
    return (
      <div style={s.forbidden}>
        <div style={s.forbiddenIcon}><UserCog size={32} /></div>
        <h3 style={s.forbiddenTitle}>Admin Access Required</h3>
        <p style={s.forbiddenText}>Only administrators can manage dentist accounts.</p>
      </div>
    );
  }

  return (
    <div className="tw-page-layout">
      {/* Header */}
      <div className="tw-page-header">
        <div className="tw-page-title-wrap">
          <h2>Staff</h2>
          <p>{dentists.length} members</p>
        </div>
        <button className="tw-primary-action-btn" onClick={openAdd}>+ Add Staff Member</button>
      </div>

      {/* Search */}
      <div style={s.searchWrap}>
        <span style={s.searchIcon}><KeyRound size={16} aria-hidden="true" /></span>
        <input
          style={s.searchInput}
          placeholder="Search by name or email..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div style={s.tableCard} className="tw-responsive-table">
        {loading ? (
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Name</th>
                <th style={s.th}>Email</th>
                <th style={s.th}>Role</th>
                <th style={s.th}>License No.</th>
                <th style={s.th}>Status</th>
                <th style={s.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              <SkeletonTableRows columns={6} rows={5} />
            </tbody>
          </table>
        ) : filtered.length === 0 ? (
          <div style={s.emptyState}>
            <div style={s.emptyIcon}><UserCog size={32} /></div>
            <h3 style={s.emptyTitle}>No staff members found</h3>
            <p style={s.emptyDesc}>Add the first staff member to get started.</p>
            <button className="tw-primary-action-btn" onClick={openAdd}>+ Add Staff Member</button>
          </div>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Name</th>
                <th style={s.th}>Email</th>
                <th style={s.th}>Role</th>
                <th style={s.th}>License No.</th>
                <th style={s.th}>Status</th>
                <th style={s.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((d, i) => (
                <tr
                  key={d.id}
                  className="stagger-item staff6-row"
                  style={{ ...s.tr, '--stagger-index': i }}
                >
                  <td style={s.td} data-label="Name">
                    <div style={s.nameCell}>
                      <div style={s.avatar}>{d.full_name.charAt(0)}</div>
                      <div>
                        <span style={s.name}>{d.full_name}</span>
                        {d.id === me?.id && (
                          <span style={s.youBadge}>You</span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td style={s.td} data-label="Email">{d.email}</td>
                  <td style={s.td} data-label="Role">
                    <span style={{
                      ...s.roleBadge,
                      background: d.role === 'admin' ? '#FCE8EA' : '#EEF2FF',
                      color: d.role === 'admin' ? '#C4505A' : '#4F46E5',
                    }}>
                      {d.role}
                    </span>
                  </td>
                  <td style={s.td} data-label="License No.">{d.license_no || '—'}</td>
                  <td style={s.td} data-label="Status">
                    <span style={{
                      ...s.statusBadge,
                      background: d.is_active ? '#E8F5EE' : '#F5F5F5',
                      color: d.is_active ? '#2D7A52' : '#999',
                    }}>
                      {d.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td style={s.td} data-label="Actions">
                    <div style={s.actions}>
                      <button style={s.actionBtn} onClick={() => openEdit(d)} title="Edit" aria-label={`Edit ${d.full_name}`}><Pencil size={15} aria-hidden="true" /></button>
                      <button style={s.actionBtn} onClick={() => openPw(d)} title="Reset Password"><KeyRound size={15} /></button>
                      {d.id !== me?.id && (
                        <>
                          <button
                            style={s.actionBtn}
                            onClick={() => handleToggleActive(d)}
                            title={d.is_active ? 'Deactivate' : 'Activate'}
                          >
                            {d.is_active ? <CircleOff size={15} /> : <CircleCheck size={15} />}
                          </button>
                          <button
                            style={{ ...s.actionBtn, ...s.deleteBtn }}
                            onClick={() => handleDelete(d)}
                            title="Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showModal && createPortal((
        <div className="tw6-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="tw6-modal" role="dialog" aria-modal="true" aria-labelledby="dentist-modal-title" onClick={e => e.stopPropagation()}>
            <div className="tw6-modal-head">
              <div className="tw6-modal-heading">
                <span className="tw6-modal-icon"><UserCog size={19} /></span>
                <div><h3 id="dentist-modal-title">{editing ? 'Edit staff member' : 'Add a staff member'}</h3></div>
              </div>
              <button className="tw6-modal-close" onClick={() => setShowModal(false)} aria-label="Close staff form"><X size={18} /></button>
            </div>
            <form onSubmit={handleSave} className="tw6-modal-form" noValidate>
              <div className="tw6-modal-section">
                <div className="tw6-modal-grid tw6-modal-grid-3">
                  <div className="tw6-modal-field">
                    <label className="tw6-modal-label">First name *</label>
                    <input className="tw6-modal-input" value={form.first_name} onChange={e => { setForm({ ...form, first_name: e.target.value }); if (formErrors.first_name) setFormErrors(f => ({ ...f, first_name: undefined })); }} placeholder="Juan" maxLength={LIMITS.NAME_MAX} required aria-invalid={!!formErrors.first_name} />
                    {formErrors.first_name && <p className="tw6-modal-error" role="alert">{formErrors.first_name}</p>}
                  </div>
                  <div className="tw6-modal-field">
                    <label className="tw6-modal-label">Middle name / initial</label>
                    <input className="tw6-modal-input" value={form.middle_name} onChange={e => { setForm({ ...form, middle_name: e.target.value }); if (formErrors.middle_name) setFormErrors(f => ({ ...f, middle_name: undefined })); }} placeholder="Santos" maxLength={LIMITS.NAME_MAX} aria-invalid={!!formErrors.middle_name} />
                    {formErrors.middle_name && <p className="tw6-modal-error" role="alert">{formErrors.middle_name}</p>}
                  </div>
                  <div className="tw6-modal-field">
                    <label className="tw6-modal-label">Last name *</label>
                    <input className="tw6-modal-input" value={form.last_name} onChange={e => { setForm({ ...form, last_name: e.target.value }); if (formErrors.last_name) setFormErrors(f => ({ ...f, last_name: undefined })); }} placeholder="Dela Cruz" maxLength={LIMITS.NAME_MAX} required aria-invalid={!!formErrors.last_name} />
                    {formErrors.last_name && <p className="tw6-modal-error" role="alert">{formErrors.last_name}</p>}
                  </div>
                </div>
              </div>
              <div className="tw6-modal-section">
                <div className="tw6-modal-grid tw6-modal-grid-2">
                  <div className="tw6-modal-field"><label className="tw6-modal-label">Email *</label><input className="tw6-modal-input" type="email" value={form.email} onChange={e => { setForm({ ...form, email: e.target.value }); if (formErrors.email) setFormErrors(f => ({ ...f, email: undefined })); }} placeholder="dentist@codismile.com" maxLength={LIMITS.EMAIL_MAX} required aria-invalid={!!formErrors.email} />{formErrors.email && <p className="tw6-modal-error" role="alert">{formErrors.email}</p>}</div>
                </div>
              </div>
              {!editing && <div className="tw6-modal-section">
                <div className="tw6-modal-field"><label className="tw6-modal-label">Password *</label>
                  <PasswordField value={form.password} onChange={v => { setForm({ ...form, password: v }); if (formErrors.password) setFormErrors(f => ({ ...f, password: undefined })); }} label="Password *" showRequirements error={formErrors.password} inputClassName="tw6-modal-input tw6-modal-input-password" labelClassName="tw6-modal-label" fieldClassName="tw6-modal-field" />
                </div></div>}
              <div className="tw6-modal-section">
                <div className="tw6-modal-grid tw6-modal-grid-2">
                  <div className="tw6-modal-field"><label className="tw6-modal-label">Role *</label><select className="tw6-modal-input" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}><option value="dentist">Dentist</option><option value="admin">Admin</option></select></div>
                  <div className="tw6-modal-field"><label className="tw6-modal-label">PRC license no.</label><input className="tw6-modal-input" value={form.license_no} onChange={e => setForm({ ...form, license_no: e.target.value })} placeholder="PRC-12345" /></div>
                </div>
              </div>
              <div className="tw6-modal-footer">
                <button type="button" className="tw6-modal-cancel" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="tw6-modal-save" disabled={saving}>{saving ? 'Saving...' : editing ? 'Save changes' : 'Add staff member'}<ArrowRight size={15} /></button>
              </div>
            </form>
          </div>
        </div>
      ), document.body)}

      {/* Password Reset Modal */}
      {showPwModal && createPortal((
        <div className="tw6-modal-overlay" onClick={() => setShowPwModal(false)}>
          <div className="tw6-modal tw6-modal-compact" role="dialog" aria-modal="true" aria-labelledby="password-modal-title" onClick={e => e.stopPropagation()}>
            <div className="tw6-modal-head"><div className="tw6-modal-heading"><span className="tw6-modal-icon"><KeyRound size={19} /></span><div><h3 id="password-modal-title">Reset password</h3></div></div><button className="tw6-modal-close" onClick={() => setShowPwModal(false)} aria-label="Close password form"><X size={18} /></button></div>
            <div className="tw6-modal-target"><div className="tw6-modal-target-mark">{pwTarget?.full_name?.charAt(0)?.toUpperCase() || 'S'}</div><div><strong>{pwTarget?.full_name}</strong><span>{pwTarget?.email}</span></div></div>
            <form onSubmit={handlePwSave} className="tw6-modal-form" noValidate>
              <PasswordField value={pwForm.new_password} onChange={v => { setPwForm({ ...pwForm, new_password: v }); if (pwErrors.new_password) setPwErrors(e => ({ ...e, new_password: undefined })); }} label="New password *" showRequirements error={pwErrors.new_password} inputClassName="tw6-modal-input tw6-modal-input-password" labelClassName="tw6-modal-label" fieldClassName="tw6-modal-field" />
              <PasswordField value={pwForm.confirm} onChange={v => { setPwForm({ ...pwForm, confirm: v }); if (pwErrors.confirm) setPwErrors(e => ({ ...e, confirm: undefined })); }} label="Confirm password *" placeholder="Repeat password" error={pwErrors.confirm} inputClassName="tw6-modal-input tw6-modal-input-password" labelClassName="tw6-modal-label" fieldClassName="tw6-modal-field" />
              <div className="tw6-modal-footer"><button type="button" className="tw6-modal-cancel" onClick={() => setShowPwModal(false)}>Cancel</button><button type="submit" className="tw6-modal-save" disabled={saving}>{saving ? 'Updating...' : 'Update password'}<ArrowRight size={15} /></button></div>
            </form>
          </div>
        </div>
      ), document.body)}
    </div>
  );
}

const s = {
  searchWrap: {
    display: 'flex', alignItems: 'center', gap: 10,
    background: WHITE, border: '1px solid #E5DADC',
    borderRadius: 11, padding: '0 16px',
    boxShadow: '0 2px 8px rgba(75,47,53,0.05)',
  },
  searchIcon: { fontSize: 16, color: MUTED },
  searchInput: {
    flex: 1, background: 'transparent', border: 'none',
    padding: '12px 0', fontSize: 14, color: BURGUNDY,
    fontFamily: 'inherit', outline: 'none',
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
  nameCell: { display: 'flex', alignItems: 'center', gap: 11 },
  avatar: {
    width: 38, height: 38, borderRadius: '50%',
    background: `linear-gradient(135deg, ${ROSE}, ${ROSEGOLD})`,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: WHITE, fontWeight: 700, fontSize: 16, flexShrink: 0,
  },
  name: { fontWeight: 600, fontSize: 14.5, color: '#352126' },
  youBadge: {
    fontSize: 10, background: '#EEF2FF', color: '#4F46E5',
    padding: '2px 8px', borderRadius: 10, fontWeight: 600,
  },
  roleBadge: {
    fontSize: 11, padding: '4px 10px', borderRadius: 10,
    fontWeight: 700, textTransform: 'capitalize',
  },
  statusBadge: {
    fontSize: 11, padding: '4px 10px', borderRadius: 10, fontWeight: 600,
  },
  actions: { display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' },
  actionBtn: {
    background: BLUSH, border: '1px solid #E5DADC', borderRadius: 8,
    padding: '6px 9px', cursor: 'pointer', fontSize: 14,
    color: BURGUNDY,
  },
  deleteBtn: { background: '#FCE8EA', border: '1px solid #F5C0C4', color: '#C4505A' },
  forbidden: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: 400, gap: 16,
  },
  forbiddenIcon: { fontSize: 48, color: MUTED },
  forbiddenTitle: { fontSize: 20, fontWeight: 700, color: BURGUNDY },
  forbiddenText: { fontSize: 14, color: MUTED, textAlign: 'center', maxWidth: 360 },
};