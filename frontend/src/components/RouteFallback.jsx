// Shown while a lazily loaded route chunk downloads. Kept tiny and
// dependency-free so it can live in the main bundle.
export default function RouteFallback() {
  return (
    <div className="tw-route-fallback" role="status" aria-live="polite">
      <span className="tw-route-fallback__spinner" aria-hidden="true" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}
