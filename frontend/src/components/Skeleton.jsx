// Skeleton loading primitives. Each renders a shimmering placeholder shaped
// like the real content it stands in for, so a loading list/table/card
// reads as "this is about to be a list/table/card" rather than a blank
// page or a spinner with no sense of layout.
//
// All shimmer styling lives in the `.skeleton` class in index.css - these
// components just size and arrange it.

export function SkeletonBlock({ width = '100%', height = 14, radius = 8, style }) {
  return <div className="skeleton" style={{ width, height, borderRadius: radius, ...style }} />;
}

export function SkeletonCircle({ size = 40, style }) {
  return <div className="skeleton" style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0, ...style }} />;
}

export function SkeletonText({ lines = 1, width, gap = 8 }) {
  const widths = Array.isArray(width) ? width : Array(lines).fill(width || '100%');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap }}>
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock key={i} width={widths[i] || '100%'} height={12} />
      ))}
    </div>
  );
}

// A single skeleton table row matching the app's <td style={s.td}> padding,
// so it lines up under the real header row while data loads.
export function SkeletonTableRow({ columns = 4, index = 0 }) {
  return (
    <tr style={{ '--stagger-index': index }} className="stagger-item">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} style={{ padding: '14px 16px' }}>
          {i === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <SkeletonCircle size={34} />
              <SkeletonBlock width={i === 0 ? 120 : 80} />
            </div>
          ) : (
            <SkeletonBlock width={i % 2 === 0 ? '70%' : '45%'} />
          )}
        </td>
      ))}
    </tr>
  );
}

export function SkeletonTableRows({ columns = 4, rows = 5 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonTableRow key={i} columns={columns} index={i} />
      ))}
    </>
  );
}

// A generic card-shaped placeholder - used for stat cards, detail panels,
// and anything else that isn't a table row.
export function SkeletonCard({ index = 0, height = 100, style }) {
  return (
    <div
      className="stagger-item"
      style={{
        '--stagger-index': index,
        background: 'var(--tw-surface)', borderRadius: 14, padding: 20,
        border: '1px solid var(--tw-border)', display: 'flex', flexDirection: 'column', gap: 10,
        minHeight: height, ...style,
      }}
    >
      <SkeletonBlock width="40%" height={11} />
      <SkeletonBlock width="65%" height={22} />
    </div>
  );
}
