import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { Search, Trash2, Pencil, X, UsersRound, ArrowRight } from 'lucide-react';
import { patientsAPI } from '../api';
import { validatePHMobile, validateRequiredText, validateOptionalText, LIMITS } from '../utils/validation';
import { SkeletonTableRows } from '../components/Skeleton';
import toast from 'react-hot-toast';

const BURGUNDY = '#4B2F35';
const ROSE = '#BA7976';
const ROSEGOLD = '#C78C8A';
const BLUSH = '#FBF7F5';
const WHITE = '#FFFFFF';
const MUTED = '#6F5B61';

const EMPTY_FORM = {
  first_name: '', middle_name: '', last_name: '', birthdate: '', gender: '', contact_number: '', address: ''
};

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState({});
  const navigate = useNavigate();

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const t = setTimeout(() => load(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    if (!showModal) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') setShowModal(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [showModal]);

  function load(s = '') {
    setLoading(true);
    patientsAPI.list(s)
      .then(r => setPatients(r.data))
      .catch(() => toast.error('Failed to load patients'))
      .finally(() => setLoading(false));
  }

  function openAdd() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setFormErrors({});
    setShowModal(true);
  }

  function openEdit(p, e) {
    e.stopPropagation();
    setEditing(p);
    setForm({
      first_name: p.first_name || '',
      middle_name: p.middle_name || '',
      last_name: p.last_name || '',
      birthdate: p.birthdate || '',
      gender: p.gender || '',
      contact_number: p.contact_number || '',
      address: p.address || '',
    });
    setFormErrors({});
    setShowModal(true);
  }

  async function handleSave(e) {
    e.preventDefault();

    const firstCheck = validateRequiredText(form.first_name, 'First name');
    const lastCheck = validateRequiredText(form.last_name, 'Last name');
    const middleCheck = validateOptionalText(form.middle_name, 'Middle name', LIMITS.NAME_MAX);
    const phoneCheck = validatePHMobile(form.contact_number, { required: false });
    const addressCheck = validateOptionalText(form.address, 'Address', LIMITS.ADDRESS_MAX);
    const nextErrors = {};
    if (!firstCheck.valid) nextErrors.first_name = firstCheck.message;
    if (!lastCheck.valid) nextErrors.last_name = lastCheck.message;
    if (!middleCheck.valid) nextErrors.middle_name = middleCheck.message;
    if (!phoneCheck.valid) nextErrors.contact_number = phoneCheck.message;
    if (!addressCheck.valid) nextErrors.address = addressCheck.message;
    if (Object.keys(nextErrors).length > 0) {
      setFormErrors(nextErrors);
      return;
    }
    setFormErrors({});

    setSaving(true);
    const payload = {
      first_name: firstCheck.value,
      middle_name: middleCheck.value || null,
      last_name: lastCheck.value,
      birthdate: form.birthdate || null,
      gender: form.gender || null,
      contact_number: phoneCheck.value || null,
      address: addressCheck.value || null,
    };
    try {
      if (editing) {
        await patientsAPI.update(editing.id, payload);
        toast.success('Patient updated!');
      } else {
        await patientsAPI.create(payload);
        toast.success('Patient registered!');
      }
      setShowModal(false);
      load(search);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(p, e) {
    e.stopPropagation();
    if (!window.confirm(`Delete ${p.full_name}? All screenings will also be deleted.`)) return;
    try {
      await patientsAPI.delete(p.id);
      toast.success('Patient deleted');
      load(search);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to delete');
    }
  }

  function calcAge(birthdate) {
    if (!birthdate) return '—';
    const diff = Date.now() - new Date(birthdate).getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25)) + ' yrs';
  }

  return (
    <div className="tw-page-layout">
      {/* Header */}
      <div className="tw-page-header">
        <div className="tw-page-title-wrap">
          <h2>Patients</h2>
          <p>{patients.length} records</p>
        </div>
        <button className="tw-primary-action-btn" onClick={openAdd}>+ Register Patient</button>
      </div>

      {/* Search */}
      <div style={s.searchWrap}>
        <span style={s.searchIcon}><Search size={16} aria-hidden="true" /></span>
        <input
          style={s.searchInput}
          placeholder="Search patients by name..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Patient list */}
      {loading ? (
        <div style={s.tableCard} className="tw-responsive-table">
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Patient</th>
                <th style={s.th}>Age</th>
                <th style={s.th}>Gender</th>
                <th style={s.th}>Contact</th>
                <th style={s.th}>Address</th>
                <th style={s.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              <SkeletonTableRows columns={6} rows={6} />
            </tbody>
          </table>
        </div>
      ) : patients.length === 0 ? (
        <div style={s.emptyState}>
          <div style={s.emptyIcon}><UsersRound size={32} /></div>
          <h3 style={s.emptyTitle}>No patients yet</h3>
          <p style={s.emptyDesc}>Add the first patient record to get started.</p>
          <button className="tw-primary-action-btn" onClick={openAdd}>+ Register Patient</button>
        </div>
      ) : (
        <div style={s.tableCard} className="tw-responsive-table">
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Patient</th>
                <th style={s.th}>Age</th>
                <th style={s.th}>Gender</th>
                <th style={s.th}>Contact</th>
                <th style={s.th}>Address</th>
                <th style={s.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p, i) => (
                <tr
                  key={p.id}
                  className="stagger-item patients6-row"
                  style={{ ...s.tr, '--stagger-index': i }}
                  onClick={() => navigate('/dashboard/patients/' + p.id)}
                >
                  <td style={s.td} data-label="Patient">
                    <div style={s.nameCell}>
                      <div style={s.avatar}>{p.full_name.charAt(0)}</div>
                      <div>
                        <div style={s.patientName}>{p.full_name}</div>
                        <div style={s.patientId}>ID #{p.id}</div>
                      </div>
                    </div>
                  </td>
                  <td style={s.td} data-label="Age">{calcAge(p.birthdate)}</td>
                  <td style={s.td} data-label="Gender">{p.gender || '—'}</td>
                  <td style={s.td} data-label="Contact">{p.contact_number || '—'}</td>
                  <td style={s.td} data-label="Address">
                    <span style={s.addressText}>{p.address || '—'}</span>
                  </td>
                  <td style={s.td} data-label="Actions">
                    <div style={s.actions}>
                      <button
                        style={s.viewBtn}
                        onClick={e => { e.stopPropagation(); navigate('/dashboard/patients/' + p.id); }}
                      >
                        View
                      </button>
                      <button style={s.editBtn} onClick={e => openEdit(p, e)} aria-label={`Edit ${p.full_name}`} title="Edit patient"><Pencil size={15} aria-hidden="true" /></button>
                      <button style={s.deleteBtn} onClick={e => handleDelete(p, e)}><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && createPortal((
        <div className="tw6-modal-overlay" onClick={() => setShowModal(false)}>
          <div className="tw6-modal" role="dialog" aria-modal="true" aria-labelledby="patient-modal-title" onClick={e => e.stopPropagation()}>
            <div className="tw6-modal-head">
              <div className="tw6-modal-heading">
                <span className="tw6-modal-icon"><UsersRound size={19} /></span>
                <div><h3 id="patient-modal-title">{editing ? 'Edit patient' : 'Register a patient'}</h3></div>
              </div>
              <button className="tw6-modal-close" onClick={() => setShowModal(false)} aria-label="Close patient form"><X size={18} /></button>
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
                  <div className="tw6-modal-field"><label className="tw6-modal-label">Birthdate</label><input className="tw6-modal-input" type="date" value={form.birthdate} onChange={e => setForm({ ...form, birthdate: e.target.value })} /></div>
                  <div className="tw6-modal-field"><label className="tw6-modal-label">Gender</label><select className="tw6-modal-input" value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}><option value="">— Select —</option><option value="Male">Male</option><option value="Female">Female</option><option value="Other">Other</option></select></div>
                </div>
              </div>
              <div className="tw6-modal-section">
                <div className="tw6-modal-field"><label className="tw6-modal-label">Contact number</label><input className="tw6-modal-input" value={form.contact_number} onChange={e => { setForm({ ...form, contact_number: e.target.value }); if (formErrors.contact_number) setFormErrors(f => ({ ...f, contact_number: undefined })); }} placeholder="09XXXXXXXXX" maxLength={LIMITS.PHONE_MAX} aria-invalid={!!formErrors.contact_number} />{formErrors.contact_number && <p className="tw6-modal-error" role="alert">{formErrors.contact_number}</p>}</div>
              </div>
              <div className="tw6-modal-section">
                <div className="tw6-modal-field"><label className="tw6-modal-label">Home address</label><textarea className="tw6-modal-input" value={form.address} onChange={e => { setForm({ ...form, address: e.target.value }); if (formErrors.address) setFormErrors(f => ({ ...f, address: undefined })); }} placeholder="Street, Barangay, City" maxLength={LIMITS.ADDRESS_MAX} aria-invalid={!!formErrors.address} />{formErrors.address && <p className="tw6-modal-error" role="alert">{formErrors.address}</p>}</div>
              </div>
              <div className="tw6-modal-footer">
                <button type="button" className="tw6-modal-cancel" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="tw6-modal-save" disabled={saving}>{saving ? 'Saving...' : editing ? 'Save changes' : 'Register patient'}<ArrowRight size={15} /></button>
              </div>
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
  patientName: { fontWeight: 600, color: BURGUNDY, fontSize: 14.5 },
  patientId: { fontSize: 10.5, color: MUTED, marginTop: 2 },
  addressText: { display: 'block', maxWidth: 180, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  actions: { display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' },
  viewBtn: {
    background: BLUSH, border: '1px solid #E5DADC', borderRadius: 8,
    padding: '6px 13px', cursor: 'pointer', fontSize: 12,
    color: BURGUNDY, fontWeight: 600, fontFamily: 'inherit',
  },
  editBtn: {
    background: BLUSH, border: '1px solid #E5DADC', borderRadius: 8,
    padding: '6px 9px', cursor: 'pointer', fontSize: 14,
    color: BURGUNDY,
  },
  deleteBtn: {
    background: '#FCE8EA', border: '1px solid #F5C0C4', borderRadius: 8,
    padding: '6px 9px', cursor: 'pointer', fontSize: 14,
    color: '#C4505A',
  },
};