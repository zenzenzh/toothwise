export default function LogoMark({ size = 44, className = '', alt = 'CodiSmile Dental Clinic' }) {
  return (
    <img
      src="/codismile/codismile-logo-transparent.png"
      alt={alt}
      className={`codismile-logo ${className}`.trim()}
      width={size}
      height={size}
      decoding="async"
      style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
    />
  );
}
