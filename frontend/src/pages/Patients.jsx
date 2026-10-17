import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Pencil, UsersRound, ArrowRight, UserPlus, SearchX, CloudOff, RotateCw } from 'lucide-react';
import { patientsAPI } from '../api';
import { useAuth } from '../context/AuthContext';
import { can } from '../utils/permissions';
import { validatePHMobile, validateRequiredText, validateOptionalText, LIMITS } from '../utils/validation';
import { SkeletonTableRows } from '../components/Skeleton';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import Modal from '../components/ui/Modal';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import FormField from '../components/ui/FormField';
import SearchField from '../components/ui/SearchField';
import toast from 'react-hot-toast';

const EMPTY_FORM = {
  first_name: '', middle_name: '', last_name: '', birthdate: '', gender: '', contact_number: '', address: ''
};

const COLUMNS = ['Patient', 'Age', 'Gender', 'Contact', 'Address', 'Actions'];

// Form order, so validation focuses the first invalid field.
const FIELD_IDS = [
  ['first_name', 'pt-first-name'],
  ['middle_name', 'pt-middle-name'],
  ['last_name', 'pt-last-name'],
  ['contact_number', 'pt-contact'],
  ['address', 'pt-address'],
];

function calcAge(birthdate) {
  if (!birthdate) return '—';
  const diff = Date.now() - new Date(birthdate).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25)) + ' yrs';
}

function PatientsTable({ children }) {
  return (
    <div className="tw-table-card tw-responsive-table">
      <table className="tw-data-table">
        <thead>
          <tr>{COLUMNS.map(c => <th key={c} scope="col" className={c === 'Address' ? 'tw-col-optional' : undefined}>{c}</th>)}</tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export default function Patients() {
  const { dentist: me } = useAuth();
  // Deleting a patient (and their screening history) is dentist-only.
  const canDelete = can(me?.role, 'deletePatient');
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState(''); // the search the current list reflects
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState({});
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();
  const searchRef = useRef(null);
  const requestId = useRef(0);
  const firstLoad = useRef(true);

  const load = useCallback((s = '') => {
    // Ignore responses from searches that were superseded while in flight.
    const id = ++requestId.current;
    setLoading(true);
    setLoadError(null);
    patientsAPI.list(s)
      .then(r => { if (id === requestId.current) { setPatients(r.data); setQuery(s); } })
      .catch(err => { if (id === requestId.current) setLoadError(err.friendlyMessage || 'Patients could not be loaded.'); })
      .finally(() => { if (id === requestId.current) setLoading(false); });
  }, []);

  useEffect(() => {
    // Load immediately on mount; debounce subsequent keystrokes.
    const delay = firstLoad.current ? 0 : 300;
    firstLoad.current = false;
    const t = setTimeout(() => load(search.trim()), delay);
    return () => clearTimeout(t);
  }, [search, load]);

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
      const firstInvalid = FIELD_IDS.find(([name]) => nextErrors[name]);
      if (firstInvalid) document.getElementById(firstInvalid[1])?.focus();
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
        toast.success('Patient updated');
      } else {
        await patientsAPI.create(payload);
        toast.success('Patient registered');
      }
      setShowModal(false);
      load(search.trim());
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await patientsAPI.delete(pendingDelete.id);
      toast.success(`${pendingDelete.full_name} deleted`);
      setPendingDelete(null);
      load(search.trim());
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to delete');
    } finally {
      setDeleting(false);
    }
  }

  const subtitle = loadError
    ? undefined
    : loading && patients.length === 0
    ? 'Loading records…'
    : query
      ? `${patients.length} ${patients.length === 1 ? 'match' : 'matches'} for “${query}”`
      : `${patients.length} ${patients.length === 1 ? 'record' : 'records'}`;

  let body;
  if (loadError) {
    body = (
      <EmptyState
        className="tw-state--card"
        role="alert"
        icon={CloudOff}
        title="Couldn't load patients"
        message={loadError}
        action={<Button variant="secondary" icon={RotateCw} onClick={() => load(search.trim())}>Try again</Button>}
      />
    );
  } else if (loading && patients.length === 0) {
    body = <PatientsTable><SkeletonTableRows columns={6} rows={6} /></PatientsTable>;
  } else if (patients.length === 0 && query) {
    body = (
      <EmptyState
        className="tw-state--card"
        icon={SearchX}
        title="No matching patients"
        message={`Nobody matches “${query}”. Check the spelling or search by last name.`}
        action={<Button variant="secondary" onClick={() => { setSearch(''); searchRef.current?.focus(); }}>Clear search</Button>}
      />
    );
  } else if (patients.length === 0) {
    body = (
      <EmptyState
        className="tw-state--card"
        icon={UsersRound}
        title="No patients yet"
        message="Register the first patient record to get started."
        action={<Button icon={UserPlus} onClick={openAdd}>Register Patient</Button>}
      />
    );
  } else {
    body = (
      <PatientsTable>
        {patients.map((p, i) => (
          <tr
            key={p.id}
            className="stagger-item patients6-row"
            style={{ '--stagger-index': i }}
            onClick={() => navigate('/dashboard/patients/' + p.id)}
          >
            <td data-label="Patient">
              <div className="tw-person">
                <div className="tw-avatar" aria-hidden="true">{p.full_name.charAt(0)}</div>
                <div className="tw-person__text">
                  <div className="tw-person__name">{p.full_name}</div>
                  <div className="tw-person__meta">ID #{p.id}</div>
                </div>
              </div>
            </td>
            <td data-label="Age">{calcAge(p.birthdate)}</td>
            <td data-label="Gender">{p.gender || '—'}</td>
            <td data-label="Contact">{p.contact_number || '—'}</td>
            <td data-label="Address" className="tw-col-optional">
              <span className="tw-cell-clip" title={p.address || undefined}>{p.address || '—'}</span>
            </td>
            <td data-label="Actions">
              <div className="tw-row-actions">
                <button
                  type="button"
                  className="tw-row-btn"
                  onClick={e => { e.stopPropagation(); navigate('/dashboard/patients/' + p.id); }}
                >
                  View
                </button>
                <button type="button" className="tw-row-btn tw-row-btn--icon" onClick={e => openEdit(p, e)} aria-label={`Edit ${p.full_name}`} title="Edit patient">
                  <Pencil size={15} aria-hidden="true" />
                </button>
                {canDelete && (
                  <button
                    type="button"
                    className="tw-row-btn tw-row-btn--icon tw-row-btn--danger"
                    onClick={e => { e.stopPropagation(); setPendingDelete(p); }}
                    aria-label={`Delete ${p.full_name}`}
                    title="Delete patient"
                  >
                    <Trash2 size={15} aria-hidden="true" />
                  </button>
                )}
              </div>
            </td>
          </tr>
        ))}
      </PatientsTable>
    );
  }

  return (
    <div className="tw-page-layout">
      <PageHeader
        title="Patients"
        subtitle={subtitle}
        actions={<Button icon={UserPlus} onClick={openAdd}>Register Patient</Button>}
      />

      <SearchField
        id="patient-search"
        ref={searchRef}
        label="Search patients by name"
        placeholder="Search patients by name…"
        value={search}
        onChange={setSearch}
      />

      <div aria-live="polite" aria-busy={loading}>{body}</div>

      <Modal
        isOpen={showModal}
        onClose={() => { if (!saving) setShowModal(false); }}
        title={editing ? 'Edit patient' : 'Register a patient'}
        icon={UsersRound}
        dismissible={!saving}
      >
        <form onSubmit={handleSave} className="tw6-modal-form" noValidate>
          <div className="tw6-modal-section">
            <div className="tw6-modal-grid tw6-modal-grid-3">
              <FormField id="pt-first-name" label="First name" required error={formErrors.first_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.first_name} onChange={e => setField('first_name', e.target.value)} placeholder="Juan" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
              <FormField id="pt-middle-name" label="Middle name / initial" error={formErrors.middle_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.middle_name} onChange={e => setField('middle_name', e.target.value)} placeholder="Santos" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
              <FormField id="pt-last-name" label="Last name" required error={formErrors.last_name}>
                {a => <input {...a} className="tw6-modal-input" value={form.last_name} onChange={e => setField('last_name', e.target.value)} placeholder="Dela Cruz" maxLength={LIMITS.NAME_MAX} autoComplete="off" />}
              </FormField>
            </div>
          </div>
          <div className="tw6-modal-section">
            <div className="tw6-modal-grid tw6-modal-grid-2">
              <FormField id="pt-birthdate" label="Birthdate">
                {a => <input {...a} className="tw6-modal-input" type="date" value={form.birthdate} max={new Date().toISOString().slice(0, 10)} onChange={e => setField('birthdate', e.target.value)} />}
              </FormField>
              <FormField id="pt-gender" label="Gender">
                {a => (
                  <select {...a} className="tw6-modal-input" value={form.gender} onChange={e => setField('gender', e.target.value)}>
                    <option value="">— Select —</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                )}
              </FormField>
            </div>
          </div>
          <div className="tw6-modal-section">
            <FormField id="pt-contact" label="Contact number" error={formErrors.contact_number}>
              {a => <input {...a} className="tw6-modal-input" type="tel" inputMode="numeric" value={form.contact_number} onChange={e => setField('contact_number', e.target.value)} placeholder="09XXXXXXXXX" maxLength={LIMITS.PHONE_MAX} autoComplete="off" />}
            </FormField>
          </div>
          <div className="tw6-modal-section">
            <FormField id="pt-address" label="Home address" error={formErrors.address}>
              {a => <textarea {...a} className="tw6-modal-input" value={form.address} onChange={e => setField('address', e.target.value)} placeholder="Street, Barangay, City" maxLength={LIMITS.ADDRESS_MAX} />}
            </FormField>
          </div>
          <div className="tw6-modal-footer">
            <button type="button" className="tw6-modal-cancel" onClick={() => setShowModal(false)} disabled={saving}>Cancel</button>
            <button type="submit" className="tw6-modal-save" disabled={saving} aria-busy={saving}>
              {saving ? 'Saving…' : editing ? 'Save changes' : 'Register patient'}
              {!saving && <ArrowRight size={15} aria-hidden="true" />}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!pendingDelete}
        onCancel={() => { if (!deleting) setPendingDelete(null); }}
        onConfirm={confirmDelete}
        busy={deleting}
        title="Delete patient?"
        message={pendingDelete ? (
          <>
            <strong>{pendingDelete.full_name}</strong> and all of their screening records will be permanently deleted. This can't be undone.
          </>
        ) : ''}
        confirmText="Delete patient"
      />
    </div>
  );
}
