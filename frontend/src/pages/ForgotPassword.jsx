import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';
import SEO from '../components/SEO';
import ForgotPasswordForm from '../components/ForgotPasswordForm';
import { authAPI, patientAuthAPI } from '../api';

// One page for both account types: ?type=staff (default) or ?type=patient.
// No email is sent: the user confirms details already on their account and
// sets a new password right here.
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
              : 'Enter your email and the PRC license number on your staff account, then choose a new password. No license number on file? Ask the clinic dentist to reset it for you.'}
          </p>
        </div>

        <ForgotPasswordForm
          key={type}
          kind={type}
          submit={isPatient ? patientAuthAPI.forgotPassword : authAPI.forgotPassword}
          onDone={() => navigate(loginPathFor(type), { replace: true })}
        />

        <div className="auth6-note">
          Remembered it?
          <div className="auth6-note-link"><Link to={loginPathFor(type)}>Back to sign in →</Link></div>
        </div>
      </AuthLayout>
    </>
  );
}
