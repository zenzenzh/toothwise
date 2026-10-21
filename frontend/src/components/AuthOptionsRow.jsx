import { useId } from 'react';
import { Link } from 'react-router-dom';

// "Remember me" checkbox and "Forgot password?" link, shown under the
// password field on the staff and patient sign-in forms.
export default function AuthOptionsRow({ remember, onRememberChange, forgotTo }) {
  const id = useId();
  return (
    <div className="auth6-options">
      <label htmlFor={id} className="auth6-remember">
        <input id={id} type="checkbox" checked={remember} onChange={e => onRememberChange(e.target.checked)} />
        <span>Remember me on this device</span>
      </label>
      <Link to={forgotTo} className="auth6-forgot">Forgot password?</Link>
    </div>
  );
}
