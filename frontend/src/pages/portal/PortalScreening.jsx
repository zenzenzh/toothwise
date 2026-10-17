import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Microscope, Star, FileX, ImageOff, RotateCw } from 'lucide-react';
import { patientScreeningsAPI } from '../../api';
import { formatDatePH } from '../../utils/datetime';
import { SkeletonBlock } from '../../components/Skeleton';
import DetectionCanvas, { CLASS_COLORS_DEEP, prettyLabel } from '../../components/DetectionCanvas';
import EmptyState from '../../components/ui/EmptyState';
import Button from '../../components/ui/Button';
import RiskBadge from '../../components/ui/RiskBadge';

export const riskPillClass = level =>
  `pp2-risk-pill pp2-risk-pill--${level === 'HIGH' ? 'high' : level === 'MEDIUM' ? 'moderate' : 'low'}`;

export default function PortalScreening({ screeningId, onBack }) {
  const [screening, setScreening] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // { notFound, message }
  const [imageUrl, setImageUrl] = useState(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const headingRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    patientScreeningsAPI.get(screeningId)
      .then(r => { if (!cancelled) setScreening(r.data); })
      .catch(err => {
        if (!cancelled) setError({ notFound: err.response?.status === 404, message: err.friendlyMessage || 'This screening could not be loaded.' });
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [screeningId, attempt]);

  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;
    setImageFailed(false);
    patientScreeningsAPI.imageObjectUrl(screeningId).then(url => {
      if (cancelled) { window.URL.revokeObjectURL(url); return; }
      objectUrl = url;
      setImageUrl(url);
    }).catch(() => { if (!cancelled) setImageFailed(true); });
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [screeningId, attempt]);

  // Move focus to the new view's heading so keyboard and screen-reader
  // users land on the content, not on the (now removed) card they clicked.
  useEffect(() => {
    if (!loading) headingRef.current?.focus();
  }, [loading]);

  const recommendations = [...(screening?.recommendations || [])].sort((a, b) => a.order_index - b.order_index);
  const detections = screening?.detections || [];

  return (
    <div className="pp2-detail-page">
      <button type="button" className="pp2-back-btn" onClick={onBack}>
        <ArrowLeft size={14} aria-hidden="true" />
        Back to screenings
      </button>

      {loading ? (
        <div className="pp2-detail-skeleton" aria-busy="true" aria-label="Loading screening">
          <SkeletonBlock height={300} radius={16} />
          <SkeletonBlock width="50%" height={22} />
          <SkeletonBlock width="35%" height={16} />
        </div>
      ) : error || !screening ? (
        error && !error.notFound ? (
          <EmptyState
            className="tw-state--card"
            role="alert"
            icon={ImageOff}
            title="Couldn't load this screening"
            message={error.message}
            action={<Button variant="secondary" icon={RotateCw} onClick={() => setAttempt(a => a + 1)}>Try again</Button>}
          />
        ) : (
          <EmptyState
            className="tw-state--card"
            icon={FileX}
            title="Screening not found"
            message="This screening is no longer available on your account."
            action={<Button variant="secondary" onClick={onBack}>Back to screenings</Button>}
          />
        )
      ) : (
        <div className="pp2-detail">
          <div className="pp2-detail-header">
            <div className="pp2-detail-title-row">
              <h2 ref={headingRef} tabIndex={-1} className="pp2-detail-title">{formatDatePH(screening.created_at)}</h2>
              <RiskBadge level={screening.risk_level} suffix="risk" size="lg" />
            </div>
          </div>

          <div className="pp2-detail-grid">
            <div className="pp2-detail-image">
              {imageFailed ? (
                <EmptyState compact icon={ImageOff} title="Image unavailable" message="Your screening photo couldn't be loaded right now." />
              ) : imageUrl ? (
                <DetectionCanvas imageUrl={imageUrl} detections={detections} colors={CLASS_COLORS_DEEP} />
              ) : (
                <div className="tw-detect-loading skeleton" aria-hidden="true" />
              )}
            </div>

            <div className="pp2-detail-info">
              <div className="pp2-detail-block">
                <h3 className="pp2-detail-block-title">
                  <Microscope size={14} aria-hidden="true" />
                  Findings
                </h3>
                {detections.length > 0 ? (
                  <ul className="pp2-detection-chips">
                    {detections.map((d, i) => (
                      <li key={i} className="pp2-detection-chip" style={{ '--chip-color': CLASS_COLORS_DEEP[d.label] || '#6F5B61' }}>
                        <span className="pp2-detection-dot" aria-hidden="true" />
                        {prettyLabel(d.label)} {(d.confidence * 100).toFixed(0)}%
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="pp2-detail-empty">No findings were detected in this screening.</p>
                )}
              </div>

              {recommendations.length > 0 && (
                <div className="pp2-detail-block">
                  <h3 className="pp2-detail-block-title">
                    <Star size={14} aria-hidden="true" />
                    Recommendations
                  </h3>
                  <ol className="pp2-rec-list">
                    {recommendations.map((r, i) => (
                      <li key={r.id} className="pp2-rec-item">
                        <span className="pp2-rec-num" aria-hidden="true">{i + 1}</span>
                        <span className="pp2-rec-text">{r.text}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              <p className="pp2-detail-disclaimer">
                These results are AI-assisted and are reviewed by your dentist. They are not a diagnosis.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
