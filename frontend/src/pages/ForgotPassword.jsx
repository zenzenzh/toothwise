import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import SEO from '../components/SEO';
import ForgotPasswordForm from '../components/ForgotPasswordForm';
import { patientAuthAPI } from '../api';

// One page for both account types: ?type=staff (default) or ?type=patient.
// Patients confirm details already on their account and set a new password
// right here. Staff passwords are reset by the clinic dentist/administrator.
export function accountTypeFrom(params) {
  return params.get('type') === 'patient' ? 'patient' : 'staff';
}

export function loginPathFor(type) {
  return type === 'patient' ? '/patient-portal' : '/login';
}

export default function ForgotPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const type = accountTypeFrom(params);
  const isPatient = type === 'patient';

  return (
    <>
      <SEO title="Forgot Password | ToothWise" description="Reset your ToothWise account password." noIndex />
      <AuthLayout>
        <div className="auth6-head">
          <h1>Reset your password</h1>
          <p>
            {isPatient
              ? 'Enter the birthdate and mobile number on your patient account, then choose a new password.'
              : 'Staff passwords are reset by the clinic dentist (administrator). Ask them to open the Staff page and use Reset password on your account.'}
          </p>
        </div>

        {isPatient && (
          <ForgotPasswordForm
            submit={patientAuthAPI.forgotPassword}
            onDone={() => navigate(loginPathFor(type), { replace: true })}
          />
        )}

        <div className="auth6-note">
          Remembered it?
          <div className="auth6-note-link"><Link to={loginPathFor(type)}>Back to sign in →</Link></div>
        </div>
      </AuthLayout>
    </>
  );
}
