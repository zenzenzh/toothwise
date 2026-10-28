import { useEffect, useRef, useState } from 'react';
import { formatDatePH } from '../../utils/datetime';

// Same cut-offs as backend/app/ml/risk_engine.py.
const BANDS = [
  { level: 'HIGH', label: 'High', from: 70, to: 100 },
  { level: 'MEDIUM', label: 'Medium', from: 35, to: 70 },
  { level: 'LOW', label: 'Low', from: 0, to: 35 },
];

const HEIGHT = 200;
const PAD = { top: 12, right: 64, bottom: 28, left: 12 };

/**
 * Risk score over time, oldest on the left. One series, so no legend:
 * the section title names it, and the shaded bands carry text labels.
 * The screening list below the chart doubles as its table view.
 */
export default function RiskTrend({ screenings, onOpen }) {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const points = [...screenings]
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .map(s => ({ ...s, t: new Date(s.created_at).getTime() }));

  const innerW = Math.max(width - PAD.left - PAD.right, 0);
  const innerH = HEIGHT - PAD.top - PAD.bottom;
  const t0 = points[0]?.t ?? 0;
  const t1 = points[points.length - 1]?.t ?? 1;
  const span = t1 - t0 || 1;
  const x = t => PAD.left + ((t - t0) / span) * innerW;
  const y = v => PAD.top + (1 - v / 100) * innerH;

  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(p.t).toFixed(1)},${y(p.risk_score).toFixed(1)}`).join(' ');
  const first = points[0];
  const last = points[points.length - 1];
  const summary = first && last
    ? `Risk score went from ${first.risk_score} on ${formatDatePH(first.created_at)} to ${last.risk_score} on ${formatDatePH(last.created_at)}, across ${points.length} screenings.`
    : '';

  return (
    <div className="pp2-trend-chart" ref={wrapRef}>
      <p className="sr-only">{summary}</p>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={summary} onMouseLeave={() => setHover(null)}>
          {BANDS.map(b => (
            <g key={b.level}>
              <rect
                className={`pp2-trend-band pp2-trend-band--${b.level.toLowerCase()}`}
                x={PAD.left} width={innerW}
                y={y(b.to)} height={y(b.from) - y(b.to)}
              />
              <text className="pp2-trend-band-label" x={PAD.left + innerW + 10} y={(y(b.to) + y(b.from)) / 2} dominantBaseline="middle">
                {b.label}
              </text>
            </g>
          ))}
          <path className="pp2-trend-line" d={path} />
          {points.map((p, i) => {
            const isEdge = i === 0 || i === points.length - 1;
            return (
              <g key={p.id}>
                {isEdge && (
                  <text
                    className="pp2-trend-axis"
                    x={x(p.t)} y={HEIGHT - 8}
                    textAnchor={i === 0 ? 'start' : 'end'}
                  >
                    {formatDatePH(p.created_at, { month: 'short', day: undefined, year: 'numeric' })}
                  </text>
                )}
                <circle className={`pp2-trend-dot pp2-trend-dot--${p.risk_level.toLowerCase()}`} cx={x(p.t)} cy={y(p.risk_score)} r={hover === i ? 6 : 4.5} />
                {/* Hit target bigger than the mark */}
                <circle
                  className="pp2-trend-hit"
                  cx={x(p.t)} cy={y(p.risk_score)} r={16}
                  onMouseEnter={() => setHover(i)}
                  onClick={() => onOpen(p.id)}
                />
              </g>
            );
          })}
        </svg>
      )}
      {hover != null && points[hover] && (
        <div
          className="pp2-trend-tip"
          style={{
            left: Math.min(Math.max(x(points[hover].t), 70), width - 70),
            top: y(points[hover].risk_score) - 12,
          }}
          aria-hidden="true"
        >
          <span className="pp2-trend-tip-date">{formatDatePH(points[hover].created_at)}</span>
          <span className="pp2-trend-tip-value">{points[hover].risk_level} risk · score {points[hover].risk_score}</span>
        </div>
      )}
    </div>
  );
}
