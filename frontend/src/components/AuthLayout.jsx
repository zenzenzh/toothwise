import LogoMark from './LogoMark';

// Shared shell for both auth surfaces (staff /login and the patient portal's
// sign-in/sign-up card): a single centered card on a calm brand-tinted
// background. Simple by default; interactivity lives in the CSS details.
export default function AuthLayout({ children }) {
  return (
    <div className="auth6">
      <div className="auth6-blob auth6-blob-a" aria-hidden="true" />
      <div className="auth6-blob auth6-blob-b" aria-hidden="true" />
      <main className="auth6-card">
        <div className="auth6-logo" aria-hidden="true"><LogoMark size={26} color="#fff" strokeWidth={7} /></div>
        {children}
      </main>
    </div>
  );
}
