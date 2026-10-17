import { useEffect, useState, useRef, useCallback } from 'react';
import DetectionCanvas, { CLASS_COLORS, FALLBACK_COLOR, prettyLabel } from '../components/DetectionCanvas';
import { FileDown, Save, ArrowLeft, FileX, CloudOff, RotateCw, ImageOff, ClipboardList, NotebookPen } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { screeningsAPI, patientsAPI } from '../api';
import { formatDatePH, formatDateTimePH } from '../utils/datetime';
import { LIMITS } from '../utils/validation';
import { SkeletonBlock, SkeletonCard } from '../components/Skeleton';
import { useAuth } from '../context/AuthContext';
import { can } from '../utils/permissions';
import Button from '../components/ui/Button';
import EmptyState from '../components/ui/EmptyState';
import toast from 'react-hot-toast';

const TABS = [
  { key: 'fused', label: 'Fused' },
  { key: 'yolov8', label: 'YOLOv8' },
  { key: 'yolov12', label: 'YOLOv12' },
];

const formatMs = ms => (typeof ms === 'number' ? ms.toFixed(1) : ms ?? '—');

function DetectionLegend({ detections }) {
  const counts = (detections || []).reduce((acc, d) => ({ ...acc, [d.label]: (acc[d.label] || 0) + 1 }), {});
  const entries = Object.entries(counts);
  if (entries.length === 0) return <p className="sd-legend-empty">No findings detected in this view.</p>;
  return (
    <ul className="sd-legend" aria-label="Findings in this view">
      {entries.map(([label, n]) => (
        <li key={label}>
          <span className="sd-legend-swatch" style={{ background: CLASS_COLORS[label] || FALLBACK_COLOR }} aria-hidden="true" />
          <span className="sd-legend-label">{prettyLabel(label)}</span>
          <span className="sd-legend-count">{n}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ScreeningDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { dentist: me } = useAuth();
  // Clinical notes are a licensed act - only the dentist writes them. The
  // assistant and dentist can both read an existing note and view results.
  const canWriteNotes = can(me?.role, 'writeClinical');
  const [screening, setScreening] = useState(null);
  const [patient, setPatient] = useState(null);
  const [noteBody, setNoteBody] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // { notFound, message }
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState(null);
  const [activeTab, setActiveTab] = useState('fused'); // 'fused' | 'yolov8' | 'yolov12'
  const [imageUrl, setImageUrl] = useState(null);
  const [imageState, setImageState] = useState('loading'); // 'loading' | 'ready' | 'error'
  const [showBoxes, setShowBoxes] = useState(true);
  const tabRefs = useRef({});

  // `quiet` refreshes after saving a note without flashing the skeleton.
  const load = useCallback((quiet = false) => {
    if (!quiet) { setLoading(true); setError(null); }
    return screeningsAPI.get(id)
      .then(r => {
        setScreening(r.data);
        return patientsAPI.get(r.data.patient_id).then(p => setPatient(p.data)).catch(() => {});
      })
      .catch(err => {
        if (quiet) { toast.error(err.friendlyMessage || 'Failed to refresh'); return; }
        setError({
          notFound: err.response?.status === 404,
          message: err.friendlyMessage || 'This screening could not be loaded.',
        });
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    setScreening(null);
    setPatient(null);
    setComparison(null);
    setCompareError(null);
    setActiveTab('fused');
    load();
  }, [load]);

  // Images are served through an authenticated endpoint, not a plain
  // public URL, so they're fetched as a blob and turned into a local
  // object URL. Must revoke it on cleanup or every screening view leaks
  // memory.
  useEffect(() => {
    if (!id) return undefined;
    let objectUrl = null;
    let cancelled = false;
    setImageUrl(null);
    setImageState('loading');
    screeningsAPI.imageObjectUrl(id).then(url => {
      if (cancelled) { window.URL.revokeObjectURL(url); return; }
      objectUrl = url;
      setImageUrl(url);
      setImageState('ready');
    }).catch(() => { if (!cancelled) setImageState('error'); });
    return () => {
      cancelled = true;
      if (objectUrl) window.URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  function loadComparison() {
    setCompareLoading(true);
    setCompareError(null);
    screeningsAPI.compare(id)
      .then(r => setComparison(r.data))
      .catch(err => setCompareError(err.friendlyMessage || 'The model comparison could not be loaded.'))
      .finally(() => setCompareLoading(false));
  }

  function selectTab(tab) {
    setActiveTab(tab);
    if (tab !== 'fused' && !comparison && !compareLoading) loadComparison();
  }

  // Arrow keys move between tabs (WAI-ARIA tabs pattern).
  function onTabKeyDown(e) {
    const i = TABS.findIndex(t => t.key === activeTab);
    let next = null;
    if (e.key === 'ArrowRight') next = TABS[(i + 1) % TABS.length];
    else if (e.key === 'ArrowLeft') next = TABS[(i - 1 + TABS.length) % TABS.length];
    else if (e.key === 'Home') next = TABS[0];
    else if (e.key === 'End') next = TABS[TABS.length - 1];
    if (!next) return;
    e.preventDefault();
    selectTab(next.key);
    tabRefs.current[next.key]?.focus();
  }

  async function saveNote(e) {
    e?.preventDefault();
    if (!noteBody.trim() || saving) return;
    if (noteBody.trim().length > LIMITS.NOTES_MAX) {
      toast.error(`Note must be ${LIMITS.NOTES_MAX} characters or fewer.`);
      return;
    }
    setSaving(true);
    try {
      await screeningsAPI.addNote(id, noteBody.trim());
      setNoteBody('');
      toast.success('Note added');
      await load(true);
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
    <div className="sd-page tw-page-layout" aria-busy="true" aria-label="Loading screening">
      <div className="sd-topbar">
        <SkeletonBlock width={160} height={40} radius={10} />
        <SkeletonBlock width={220} height={20} />
      </div>
      <SkeletonCard height={90} />
      <div className="sd-main-grid">
        <SkeletonCard height={360} />
        <SkeletonCard height={360} />
      </div>
    </div>
  );

  if (error || !screening) {
    return (
      <div className="sd-page tw-page-layout">
        <div><Button variant="secondary" icon={ArrowLeft} onClick={() => navigate(-1)}>Go back</Button></div>
        {error?.notFound || !error ? (
          <EmptyState
            className="tw-state--card"
            icon={FileX}
            title="Screening not found"
            message="This screening may have been deleted, or the link is incorrect."
            action={<Button variant="secondary" onClick={() => navigate('/dashboard/patients')}>Go to Patients</Button>}
          />
        ) : (
          <EmptyState
            className="tw-state--card"
            role="alert"
            icon={CloudOff}
            title="Couldn't load this screening"
            message={error.message}
            action={<Button variant="secondary" icon={RotateCw} onClick={() => load()}>Try again</Button>}
          />
        )}
      </div>
    );
  }

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
  const activeLabel = TABS.find(t => t.key === activeTab)?.label;
  const comparing = activeTab !== 'fused';

  let imagePanel;
  if (imageState === 'loading') {
    imagePanel = <div className="sd-image-placeholder skeleton" aria-label="Loading image" />;
  } else if (imageState === 'error' || !imageUrl) {
    imagePanel = (
      <EmptyState compact icon={ImageOff} title="Image unavailable" message="The screening image could not be loaded." className="sd-image-placeholder" />
    );
  } else if (comparing && compareLoading) {
    imagePanel = <div className="sd-image-placeholder skeleton" role="status">Loading {activeLabel} detections…</div>;
  } else if (comparing && compareError) {
    imagePanel = (
      <EmptyState
        compact
        role="alert"
        icon={CloudOff}
        title={`Couldn't load ${activeLabel} results`}
        message={compareError}
        className="sd-image-placeholder"
        action={<Button variant="secondary" size="sm" icon={RotateCw} onClick={loadComparison}>Try again</Button>}
      />
    );
  } else {
    imagePanel = <DetectionCanvas imageUrl={imageUrl} detections={tabDetections} showBoxes={showBoxes} />;
  }

  return (
    <div className="sd-page tw-page-layout">
      {/* TOP BAR */}
      <div className="sd-topbar">
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/dashboard/patients/' + screening.patient_id)}>Back to Patient</Button>
        <div className="sd-topbar-right">
          <span className="sd-date">Screened {formatDatePH(screening.created_at)}</span>
          <Button variant="secondary" icon={FileDown} onClick={downloadPdfReport} disabled={downloadingPdf} aria-busy={downloadingPdf}>
            {downloadingPdf ? 'Generating…' : 'Download PDF Report'}
          </Button>
        </div>
      </div>

      {/* PATIENT HEADER + RISK BADGE */}
      <section className="sd-card sd-patient-header" aria-label="Screening summary">
        <div className="sd-patient-text">
          <p className="sd-eyebrow">AI analysis result · Screening #{screening.id}</p>
          <h1 className="sd-patient-name">{patient?.full_name || `Patient #${screening.patient_id}`}</h1>
        </div>
        <div className={`sd-risk sd-risk--${screening.risk_level}`}>
          <div className="sd-risk-label">Risk level</div>
          <div className="sd-risk-value">{screening.risk_level}</div>
          <div className="sd-risk-count">{fusedDetections.length} finding{fusedDetections.length !== 1 ? 's' : ''}</div>
        </div>
      </section>

      {/* MAIN GRID: image left, plan+notes right */}
      <div className="sd-main-grid">
        {/* LEFT COLUMN: IMAGE */}
        <section className="sd-card" aria-labelledby="sd-view-title">
          <div className="sd-view-head">
            <h3 id="sd-view-title" className="sd-sec-title">AI detection view</h3>
            <label className="sd-toggle">
              <input type="checkbox" checked={showBoxes} onChange={e => setShowBoxes(e.target.checked)} />
              Show bounding boxes
            </label>
          </div>
          <div className="sd-tab-bar" role="tablist" aria-label="Detection model" onKeyDown={onTabKeyDown}>
            {TABS.map(t => (
              <button
                key={t.key}
                ref={el => { tabRefs.current[t.key] = el; }}
                type="button"
                role="tab"
                id={`sd-tab-${t.key}`}
                aria-selected={activeTab === t.key}
                aria-controls="sd-tabpanel"
                tabIndex={activeTab === t.key ? 0 : -1}
                onClick={() => selectTab(t.key)}
                className={`sd-tab-btn ${activeTab === t.key ? 'active' : ''}`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div id="sd-tabpanel" role="tabpanel" aria-labelledby={`sd-tab-${activeTab}`}>
            {imagePanel}
            {imageState === 'ready' && !(comparing && (compareLoading || compareError)) && (
              <DetectionLegend detections={tabDetections} />
            )}

            {comparing && comparison && !compareLoading && (
              <div className="sd-comparison">
                {(() => {
                  const stats = activeTab === 'yolov8' ? comparison.yolov8 : comparison.yolov12;
                  return (
                    <dl className="sd-comparison-stats">
                      <div><dt>Detections</dt><dd>{stats.detection_count}</dd></div>
                      <div><dt>Avg. confidence</dt><dd>{stats.avg_confidence != null ? (stats.avg_confidence * 100).toFixed(1) + '%' : '—'}</dd></div>
                      <div><dt>Inference</dt><dd>{formatMs(stats.inference_ms)} ms</dd></div>
                    </dl>
                  );
                })()}
                <div className="sd-comparison-summary">
                  Fused result: <strong>{comparison.fused_count}</strong> finding{comparison.fused_count !== 1 ? 's' : ''}
                  {' · '}Models agreed on <strong>{comparison.agreement_count}</strong>
                </div>
              </div>
            )}
          </div>

          <p className="sd-perf">
            YOLOv8 {formatMs(screening.yolov8_ms)} ms · YOLOv12 {formatMs(screening.yolov12_ms)} ms
          </p>
        </section>

        {/* RIGHT COLUMN: PLAN & NOTES */}
        <div className="sd-side">
          <section className="sd-card" aria-labelledby="sd-plan-title">
            <h3 id="sd-plan-title" className="sd-sec-title">Prevention plan</h3>
            {recommendations.length > 0 ? (
              <ul className="sd-recs">
                {recommendations.map((r, i) => (
                  <li key={r.id} className={`sd-rec stagger-item ${r.priority > 0 ? 'sd-rec--urgent' : ''}`.trim()} style={{ '--stagger-index': i }}>
                    {r.priority > 0 && <span className="sd-rec-flag">Urgent</span>}
                    <span className="sd-rec-text">{r.text}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState compact icon={ClipboardList} title="No recommendations" message="No specific recommendations were generated for this screening." />
            )}
          </section>

          <section className="sd-card" aria-labelledby="sd-notes-title">
            <h3 id="sd-notes-title" className="sd-sec-title">Clinical notes</h3>
            {notes.length > 0 ? (
              <ul className="sd-notes">
                {notes.map(n => (
                  <li key={n.id} className="sd-note">
                    <p className="sd-note-body">{n.body}</p>
                    <time className="sd-note-time" dateTime={n.created_at}>{formatDateTimePH(n.created_at)}</time>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="sd-muted">No clinical notes yet.</p>
            )}
            {canWriteNotes ? (
              <form className="sd-note-form" onSubmit={saveNote}>
                <label htmlFor="sd-note-input" className="sr-only">New clinical note</label>
                <textarea
                  id="sd-note-input"
                  className="sd-inp"
                  value={noteBody}
                  onChange={e => setNoteBody(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) saveNote(e); }}
                  placeholder="Add a dentist observation…"
                  maxLength={LIMITS.NOTES_MAX}
                  aria-describedby="sd-note-count"
                />
                <div className="sd-note-meta">
                  <span id="sd-note-count" className="sd-muted">
                    {noteBody.length}/{LIMITS.NOTES_MAX} · Ctrl+Enter to save
                  </span>
                </div>
                <Button type="submit" icon={saving ? undefined : Save} disabled={saving || !noteBody.trim()} aria-busy={saving} className="sd-note-submit">
                  {saving ? 'Saving…' : 'Add clinical note'}
                </Button>
              </form>
            ) : (
              <p className="sd-muted sd-note-lock"><NotebookPen size={14} aria-hidden="true" /> Only the dentist can add clinical notes.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
