import { useEffect, useState, useRef, useCallback } from 'react';
import { FileDown, Save } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { screeningsAPI, patientsAPI } from '../api';
import { formatDatePH, formatDateTimePH } from '../utils/datetime';
import { LIMITS } from '../utils/validation';
import { SkeletonBlock, SkeletonCard } from '../components/Skeleton';
import toast from 'react-hot-toast';
import T from '../tokens';

const C = T;

// Matches app/ml/labels.py LABELS on the backend.
const CLASS_COLORS = {
  healthy_tooth:       '#22C55E',
  cavity:              '#EF4444',
  gum_inflammation:    '#F97316',
  plaque:              '#EAB308',
  tartar:              '#B45309',
};

function BoundingBoxCanvas({ imageUrl, detections, showBoxes = true }) {
  const canvasRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);

  useEffect(() => {
    if (!imageUrl || !detections) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);

      if (showBoxes) {
        detections.forEach(d => {
          // x1/y1/x2/y2 are normalized (0-1) corner coordinates.
          const x = d.x1 * img.naturalWidth;
          const y = d.y1 * img.naturalHeight;
          const w = (d.x2 - d.x1) * img.naturalWidth;
          const h = (d.y2 - d.y1) * img.naturalHeight;

          const color = CLASS_COLORS[d.label] || '#FF0000';
          ctx.strokeStyle = color;
          ctx.lineWidth = Math.max(4, img.naturalWidth / 200);
          ctx.strokeRect(x, y, w, h);

          const label = `${d.label.replace(/_/g, ' ')} ${(d.confidence * 100).toFixed(0)}%`;
          const fontSize = Math.max(14, img.naturalWidth / 40);
          ctx.font = `bold ${fontSize}px Arial`;
          const textW = ctx.measureText(label).width;

          ctx.fillStyle = color;
          ctx.fillRect(x, y - fontSize - 10, textW + 10, fontSize + 10);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(label, x + 5, y - 8);
        });
      }
      setImgLoaded(true);
    };
    img.src = imageUrl;
  }, [imageUrl, detections, showBoxes]);

  return (
    <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', background: 'var(--tw-surface)', width: '100%' }}>
      <img src={imageUrl} alt="Screening" style={{ width: '100%', display: imgLoaded ? 'none' : 'block' }} />
      <canvas ref={canvasRef} style={{ width: '100%', display: imgLoaded ? 'block' : 'none', height: 'auto' }} />
      {detections?.length > 0 && (
        <ul style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', margin: -1, padding: 0, border: 0 }}>
          {detections.map((d, i) => (
            <li key={i}>{d.label.replace(/_/g, ' ')} detected with {(d.confidence * 100).toFixed(0)}% confidence</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ScreeningDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [screening, setScreening] = useState(null);
  const [patient, setPatient] = useState(null);
  const [noteBody, setNoteBody] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('fused'); // 'fused' | 'yolov8' | 'yolov12'
  const [imageUrl, setImageUrl] = useState(null);
  const [showBoxes, setShowBoxes] = useState(true);

  const load = useCallback(() => {
    screeningsAPI.get(id)
      .then(r => {
        setScreening(r.data);
        return patientsAPI.get(r.data.patient_id);
      })
      .then(r => setPatient(r.data))
      .catch(err => toast.error(err.friendlyMessage || 'Failed to load screening details'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Images are served through an authenticated endpoint, not a plain
  // public URL, so they're fetched as a blob and turned into a local
  // object URL. Must revoke it on cleanup or every screening view leaks
  // memory.
  useEffect(() => {
    if (!id) return;
    let objectUrl = null;
    let cancelled = false;
    screeningsAPI.imageObjectUrl(id).then(url => {
      if (cancelled) { window.URL.revokeObjectURL(url); return; }
      objectUrl = url;
      setImageUrl(url);
    }).catch(() => setImageUrl(null));
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  function selectTab(tab) {
    setActiveTab(tab);
    if (tab !== 'fused' && !comparison && !compareLoading) {
      setCompareLoading(true);
      screeningsAPI.compare(id)
        .then(r => setComparison(r.data))
        .catch(err => toast.error(err.friendlyMessage || 'Failed to load model comparison'))
        .finally(() => setCompareLoading(false));
    }
  }

  async function saveNote() {
    if (!noteBody.trim() || saving) return;
    if (noteBody.trim().length > LIMITS.NOTES_MAX) {
      toast.error(`Note must be ${LIMITS.NOTES_MAX} characters or fewer.`);
      return;
    }
    setSaving(true);
    try {
      await screeningsAPI.addNote(id, noteBody.trim());
      setNoteBody('');
      toast.success('Note added!');
      load();
    } catch (err) { toast.error(err.friendlyMessage || 'Failed to save note'); }
    finally { setSaving(false); }
  }

  async function downloadPdfReport() {
    if (downloadingPdf) return; // guard against double-submit
    setDownloadingPdf(true);
    try {
      const { url, filename } = await screeningsAPI.downloadReportPdf(id);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.friendlyMessage || 'Failed to generate PDF report');
    } finally {
      setDownloadingPdf(false);
    }
  }

  if (loading) return (
    <div className="sd-page tw-page-layout">
      <div className="sd-topbar">
        <SkeletonBlock width={160} height={36} radius={10} />
        <SkeletonBlock width={220} height={20} />
      </div>
      <SkeletonCard height={70} />
      <div className="sd-main-grid">
        <SkeletonCard height={360} />
        <SkeletonCard height={360} />
      </div>
    </div>
  );
  if (!screening) return <div style={{ textAlign: 'center', padding: 100 }}>Screening not found.</div>;

  // Only the fused/clinical detection set drives the overlay + risk
  // display - the raw yolov8_raw / yolov12_raw rows exist for a future
  // model-comparison view, not this page.
  const fusedDetections = (screening.detections || []).filter(d => d.detection_set === 'fused');
  const tabDetections =
    activeTab === 'yolov8' ? (comparison?.yolov8?.detections || []) :
    activeTab === 'yolov12' ? (comparison?.yolov12?.detections || []) :
    fusedDetections;
  const recommendations = screening.recommendations || [];
  const notes = screening.notes || [];

  return (
    <div className="sd-page tw-page-layout">
      {/* TOP BAR */}
      <div className="sd-topbar">
        <button className="tw-secondary-action-btn" onClick={() => navigate('/dashboard/patients/' + screening.patient_id)}>← Back to Patient</button>
        <div className="sd-topbar-right">
          <span style={{ color: C.muted, fontSize: 13 }}>Screening Date: {formatDatePH(screening.created_at)}</span>
          <button className="tw-secondary-action-btn" onClick={downloadPdfReport} disabled={downloadingPdf}>
            {downloadingPdf ? 'Generating...' : <><FileDown size={16} /> Download PDF Report</>}
          </button>
        </div>
      </div>

      {/* PATIENT HEADER + RISK BADGE */}
      <div className="sd-card">
        <div className="sd-patient-header">
          <div>
            <h2 style={{ color: C.burgundy, margin: 0, fontSize: 'clamp(16px, 4vw, 22px)' }}>Patient: {patient?.full_name}</h2>
            <p style={{ color: C.rose, margin: '4px 0 0', fontWeight: 500 }}>AI Analysis Result</p>
          </div>
          <div className={`sd-risk sd-risk--${screening.risk_level}`}>
            <div className="sd-risk-label">Risk Level</div>
            <div className="sd-risk-value">{screening.risk_level}</div>
            <div className="sd-risk-count">{fusedDetections.length} finding{fusedDetections.length !== 1 ? 's' : ''}</div>
          </div>
        </div>
      </div>

      {/* MAIN GRID: image left, plan+notes right */}
      <div className="sd-main-grid">

          {/* LEFT COLUMN: IMAGE */}
          <div className="sd-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <h4 className="sd-sec-title">AI Detection View</h4>
              <div className="sd-tab-bar" style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                {[
                  { key: 'fused', label: 'Fused' },
                  { key: 'yolov8', label: 'YOLOv8' },
                  { key: 'yolov12', label: 'YOLOv12' },
                ].map(t => (
                  <button
                    key={t.key}
                    onClick={() => selectTab(t.key)}
                    className={`sd-tab-btn ${activeTab === t.key ? 'active' : ''}`}
                  >
                    {t.label}
                  </button>
                ))}
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 600, color: C.muted, cursor: 'pointer', marginLeft: 'auto' }}>
                  <input
                    type="checkbox"
                    checked={showBoxes}
                    onChange={e => setShowBoxes(e.target.checked)}
                    style={{ accentColor: C.burgundy, width: 16, height: 16 }}
                  />
                  Show Bounding Boxes
                </label>
              </div>
            </div>

            <div style={{ marginTop: 15 }}>
              {!imageUrl ? (
                <div className="sd-image-placeholder">
                  No image data available
                </div>
              ) : activeTab !== 'fused' && compareLoading ? (
                <div className="sd-image-placeholder">
                  Loading {activeTab === 'yolov8' ? 'YOLOv8' : 'YOLOv12'} detections...
                </div>
              ) : (
                <BoundingBoxCanvas imageUrl={imageUrl} detections={tabDetections} showBoxes={showBoxes} />
              )}
            </div>

            <p className="sd-perf">
              YOLOv8: {screening.yolov8_ms?.toFixed?.(1) ?? screening.yolov8_ms} ms · YOLOv12: {screening.yolov12_ms?.toFixed?.(1) ?? screening.yolov12_ms} ms
            </p>

            {activeTab !== 'fused' && comparison && (
              <div className="sd-comparison">
                {(() => {
                  const stats = activeTab === 'yolov8' ? comparison.yolov8 : comparison.yolov12;
                  return (
                    <div className="sd-comparison-stats">
                      <div>Detections found: <strong>{stats.detection_count}</strong></div>
                      <div>Average confidence: <strong>{stats.avg_confidence != null ? (stats.avg_confidence * 100).toFixed(1) + '%' : '—'}</strong></div>
                      <div>Inference time: <strong>{stats.inference_ms?.toFixed?.(1) ?? stats.inference_ms} ms</strong></div>
                    </div>
                  );
                })()}
                <div className="sd-comparison-summary">
                  Fused result: <strong>{comparison.fused_count}</strong> finding{comparison.fused_count !== 1 ? 's' : ''}
                  {' · '}Models agreed on <strong>{comparison.agreement_count}</strong>
                </div>
              </div>
            )}
          </div>

          {/* RIGHT COLUMN: PLAN & NOTES */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
            <div className="sd-card">
              <h4 className="sd-sec-title">Prevention Plan</h4>
              <div style={{ marginTop: 15, display: 'flex', flexDirection: 'column', gap: 10 }}>
                {recommendations.length > 0 ? (
                  recommendations.map((r, i) => (
                    <div key={r.id} className="stagger-item" style={{
                      '--stagger-index': i,
                      padding: '14px',
                      background: r.priority > 0 ? 'var(--tw-danger-bg)' : T.blush,
                      borderRadius: 10,
                    }}>
                      {r.priority > 0 && (
                        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--tw-danger)', textTransform: 'uppercase', marginBottom: 4 }}>
                          Urgent
                        </div>
                      )}
                      <div style={{ fontSize: 13, color: 'var(--tw-text)', lineHeight: 1.5 }}>{r.text}</div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: C.muted, fontSize: 13 }}>No specific recommendations generated.</p>
                )}
              </div>
            </div>

            <div className="sd-card">
              <h4 className="sd-sec-title">Clinical Notes</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12, maxHeight: 220, overflowY: 'auto' }}>
                {notes.length > 0 ? notes.map(n => (
                  <div key={n.id} style={{ padding: '10px 12px', background: T.blush, borderRadius: 8 }}>
                    <div style={{ fontSize: 13, color: 'var(--tw-text)' }}>{n.body}</div>
                    <div style={{ fontSize: 10, color: C.muted, marginTop: 4 }}>
                      {formatDateTimePH(n.created_at)}
                    </div>
                  </div>
                )) : (
                  <p style={{ color: C.muted, fontSize: 13, margin: 0 }}>No clinical notes yet.</p>
                )}
              </div>
              <textarea
                className="sd-inp"
                style={{ minHeight: 90, width: '100%', marginTop: 12, boxSizing: 'border-box', resize: 'vertical' }}
                value={noteBody}
                onChange={e => setNoteBody(e.target.value)}
                placeholder="Add a dentist observation..."
                maxLength={LIMITS.NOTES_MAX}
              />
              <button className="sd-pri-btn" style={{ width: '100%', marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }} onClick={saveNote} disabled={saving || !noteBody.trim()}>
                {saving ? 'Saving...' : <><Save size={16} /> Add Clinical Note</>}
              </button>
            </div>
          </div>
        </div>
      </div>
  );
}
