import { useState, useId } from 'react';
import { Eye, EyeOff, Check } from 'lucide-react';
import { passwordRequirements } from '../utils/validation';

const BURGUNDY = '#4B2F35';
const MUTED = '#6F5B61';
const BLUSH = '#FBF7F5';
const BORDER = '#E5DADC';
const GOOD = '#2D7A52';

/**
 * Password input with a show/hide toggle (accessible - real <button> with
 * aria-label and aria-pressed, never relies on color alone) and an
 * optional live checklist of the password policy.
 *
 * Never logs, and never echoes, the value anywhere other than the input
 * itself and the field it's bound to.
 */
export default function PasswordField({
  value,
  onChange,
  label = 'Password',
  placeholder,
  showRequirements = false,
  autoComplete = 'new-password',
  required = true,
  error,
  inputStyle,
  labelStyle,
  fieldStyle,
  inputClassName,
  labelClassName,
  fieldClassName,
}) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  const reqs = showRequirements ? passwordRequirements(value) : null;

  return (
    <div className={fieldClassName} style={fieldClassName ? undefined : (fieldStyle || s.field)}>
      {label && <label htmlFor={id} className={labelClassName} style={labelClassName ? undefined : (labelStyle || s.label)}>{label}</label>}
      <div style={s.inputWrap}>
        <input
          id={id}
          className={inputClassName}
          style={inputClassName ? { paddingRight: 44 } : { ...(inputStyle || s.input), paddingRight: 44 }}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder || '••••••••'}
          autoComplete={autoComplete}
          required={required}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
        />
        <button
          type="button"
          onClick={() => setVisible(v => !v)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          style={s.toggleBtn}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {error && <p id={`${id}-error`} style={s.error} role="alert">{error}</p>}
      {showRequirements && (
        <ul style={s.reqList} aria-label="Password requirements">
          {reqs.map(r => (
            <li key={r.key} style={{ ...s.reqItem, color: r.met ? GOOD : MUTED }}>
              {r.met ? <Check size={14} aria-hidden="true" /> : <span aria-hidden="true">—</span>} {r.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const s = {
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: { fontSize: 12, color: BURGUNDY, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' },
  inputWrap: { position: 'relative', display: 'flex' },
  input: {
    background: BLUSH, border: `1.5px solid ${BORDER}`, borderRadius: 10, color: BURGUNDY,
    padding: '12px 16px', fontSize: 14, outline: 'none', fontFamily: 'inherit', width: '100%', boxSizing: 'border-box',
  },
  toggleBtn: {
    position: 'absolute', right: 4, top: '50%', transform: 'translateY(-50%)',
    background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 16,
    padding: '6px 8px', lineHeight: 1,
  },
  error: { fontSize: 11.5, color: '#C4505A', margin: '2px 0 0 0' },
  reqList: { listStyle: 'none', margin: '2px 0 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: 2 },
  reqItem: { fontSize: 11, transition: 'color 0.15s' },
};
