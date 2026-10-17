// Small pre-sized logo variants (public/codismile/codismile-logo-{96,192})
// replace the 351 KB source PNG, which only ever renders at ~20-48 px.
export default function LogoMark({ size = 44, className = '', alt = 'CodiSmile Dental Clinic' }) {
  const base = size > 48 ? 192 : 96;
  return (
    <picture style={{ display: 'contents' }}>
      <source
        type="image/webp"
        srcSet={`/codismile/codismile-logo-${base}.webp 1x, /codismile/codismile-logo-192.webp 2x`}
      />
      <img
        src={`/codismile/codismile-logo-${base}.png`}
        srcSet={`/codismile/codismile-logo-${base}.png 1x, /codismile/codismile-logo-192.png 2x`}
        alt={alt}
        className={`codismile-logo ${className}`.trim()}
        width={size}
        height={size}
        decoding="async"
        style={{ width: size, height: size, objectFit: 'contain', display: 'block' }}
      />
    </picture>
  );
}
