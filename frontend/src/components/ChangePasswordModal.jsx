import { useState } from 'react';
import { KeyRound, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import Modal from './ui/Modal';
import PasswordField from './PasswordField';
import { validatePassword } from '../utils/validation';

const EMPTY = { current: '', next: '', confirm: '' };

// Lets a signed-in staff member or patient change their own password.
// `changePassword(current, next)` is authAPI.changePassword or
// patientAuthAPI.changePassword.
export default function ChangePasswordModal({ isOpen, onClose, changePassword }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  function close() {
    if (saving) return;
    setForm(EMPTY);
    setErrors({});
    onClose();
  }

  function set(key, value) {
    setForm(f => ({ ...f, [key]: value }));
    if (errors[key]) setErrors(e => ({ ...e, [key]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (saving) return;
    const check = validatePassword(form.next);
    const next = {};
    if (!form.current) next.current = 'Enter your current password.';
    if (!check.valid) next.next = check.message;
    else if (form.next === form.current) next.next = 'Choose a password different from your current one.';
    else if (form.next !== form.confirm) next.confirm = 'Passwords do not match.';
    if (Object.keys(next).length) { setErrors(next); return; }
    setErrors({});
    setSaving(true);
    try {
      await changePassword(form.current, form.next);
      toast.success('Password changed');
      setForm(EMPTY);
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 400 && typeof detail === 'string' && /current password/i.test(detail)) {
        setErrors({ current: detail });
      } else {
        toast.error(err.friendlyMessage || 'Could not change your password.');
      }
    } finally {
      setSaving(false);
    }
  }

  const fieldProps = {
    inputClassName: 'tw6-modal-input tw6-modal-input-password',
    labelClassName: 'tw6-modal-label',
    fieldClassName: 'tw6-modal-field',
  };

  return (
    <Modal isOpen={isOpen} onClose={close} title="Change password" icon={KeyRound} className="tw6-modal-compact" dismissible={!saving}>
      <form onSubmit={handleSubmit} className="tw6-modal-form" noValidate>
        <PasswordField value={form.current} onChange={v => set('current', v)} label="Current password" autoComplete="current-password" error={errors.current} {...fieldProps} />
        <PasswordField value={form.next} onChange={v => set('next', v)} label="New password" showRequirements error={errors.next} {...fieldProps} />
        <PasswordField value={form.confirm} onChange={v => set('confirm', v)} label="Confirm new password" placeholder="Repeat password" error={errors.confirm} {...fieldProps} />
        <div className="tw6-modal-footer">
          <button type="button" className="tw6-modal-cancel" onClick={close} disabled={saving}>Cancel</button>
          <button type="submit" className="tw6-modal-save" disabled={saving} aria-busy={saving}>
            {saving ? 'Saving…' : 'Change password'}
            {!saving && <ArrowRight size={15} aria-hidden="true" />}
          </button>
        </div>
      </form>
    </Modal>
  );
}
