import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Upload, RefreshCw, ScanLine, CheckCircle2, ArrowLeft, ArrowRight, Info, Check } from 'lucide-react';
import api, { patientsAPI, screeningsAPI } from '../api';
import { validateImageFile, ALLOWED_IMAGE_TYPES, MAX_IMAGE_BYTES } from '../utils/validation';
import Button from '../components/ui/Button';
import RiskBadge from '../components/ui/RiskBadge';
import toast from 'react-hot-toast';

const STEPS = [
  { key: 'upload', label: 'Choose image' },
  { key: 'preview', label: 'Review & analyse' },
  { key: 'results', label: 'Results' },
];
const MAX_MB = Math.round(MAX_IMAGE_BYTES / (1024 * 1024));

function formatBytes(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function Stepper({ current }) {
  const currentIndex = STEPS.findIndex(s => s.key === current);
  return (
    <ol className="scr-steps" aria-label="Screening progress">
      {STEPS.map((s, i) => {
        const state = i < currentIndex ? 'done' : i === currentIndex ? 'current' : 'todo';
        return (
          <li key={s.key} className={`scr-step scr-step--${state}`} aria-current={state === 'current' ? 'step' : undefined}>
            <span className="scr-step-dot" aria-hidden="true">{state === 'done' ? <Check size={13} strokeWidth={3} /> : i + 1}</span>
            <span className="scr-step-label">{s.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function Screening() {
  const { id: patientId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const dragDepth = useRef(0);

  const [step, setStep] = useState('upload'); // 'upload' | 'preview' | 'results'
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [screening, setScreening] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState(null);
  const [patientName, setPatientName] = useState(null);

  // AI inference can be switched off server-side (DETECTION_ENABLED=false)
  // e.g. when presenting without the models. The health endpoint is the
  // public source of truth for that switch.
  const [detectionEnabled, setDetectionEnabled] = useState(true);
  useEffect(() => {
    api.get('/health').then(({ data }) => {
      if (data && data.detection_enabled === false) setDetectionEnabled(false);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    patientsAPI.get(patientId).then(r => setPatientName(r.data?.full_name)).catch(() => {});
  }, [patientId]);

  // Object URLs are cheaper than data URLs for large photos; release them.
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  function handleFileSelect(file) {
    if (!file) return;
    const check = validateImageFile(file);
    if (!check.valid) {
      setFileError(check.message);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setFileError(null);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setStep('preview');
  }

  function openPicker() {
    fileInputRef.current?.click();
  }

  function handleDragEnter(e) {
    e.preventDefault();
    dragDepth.current += 1;
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    // Child elements fire their own enter/leave; only clear on the last one.
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    dragDepth.current = 0;
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files?.[0]);
  }

  function resetUpload() {
    setSelectedFile(null);
    setPreviewUrl(null);
    setScreening(null);
    setFileError(null);
    setStep('upload');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function runDetection() {
    if (loading) return; // guard against double-submit
    if (!detectionEnabled) {
      toast.error('AI screening is temporarily unavailable.');
      return;
    }
    const check = validateImageFile(selectedFile);
    if (!check.valid) {
      toast.error(check.message);
      return;
    }
    setLoading(true);
    try {
      // Single request: backend creates the screening AND runs the
      // YOLOv8/YOLOv12 ensemble + risk scoring + KNN recommendations
      // synchronously, returning the full result.
      const { data: result } = await screeningsAPI.create(patientId, selectedFile);
      setScreening(result);
      setStep('results');
    } catch (err) {
      toast.error(err.friendlyMessage || 'Detection failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const fused = (screening?.detections || []).filter(d => !d.detection_set || d.detection_set === 'fused');
  const detectionCount = screening?.detection_count ?? fused.length;

  return (
    <div className="screening-page tw-page-layout scr-page">
      <div>
        <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate('/dashboard/patients/' + patientId)} disabled={loading}>
          Back to Patient
        </Button>
      </div>

      <div className="tw-page-title-wrap">
        <h1>New AI Screening</h1>
        <p>{patientName ? `${patientName} · Patient #${patientId}` : `Patient #${patientId}`}</p>
      </div>

      <Stepper current={step} />

      {!detectionEnabled && step !== 'results' && (
        <div className="scr-notice" role="status">
          <Info size={16} aria-hidden="true" />
          <span>AI screening is temporarily unavailable. You can still choose an image, but analysis is switched off on the server.</span>
        </div>
      )}

      {step === 'upload' && (
        <section className="scr-card">
          <div
            className={`scr-drop ${isDragging ? 'is-dragging' : ''} ${fileError ? 'has-error' : ''}`.trim()}
            role="button"
            tabIndex={0}
            aria-describedby={fileError ? 'scr-file-error' : 'scr-file-hint'}
            onClick={openPicker}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPicker(); } }}
            onDragEnter={handleDragEnter}
            onDragOver={e => e.preventDefault()}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <span className="scr-drop-icon" aria-hidden="true"><Upload size={26} strokeWidth={1.75} /></span>
            <span className="scr-drop-title">{isDragging ? 'Drop the image to upload' : 'Upload a dental image'}</span>
            <span id="scr-file-hint" className="scr-drop-hint">
              Drag and drop here, or click to browse. JPEG, PNG or WebP, up to {MAX_MB} MB.
            </span>
            <span className="tw-btn tw-btn--primary scr-drop-btn" aria-hidden="true">Choose image</span>
          </div>
          {fileError && <p id="scr-file-error" className="scr-error" role="alert">{fileError}</p>}
          <input
            ref={fileInputRef}
            type="file"
            accept={ALLOWED_IMAGE_TYPES.join(',')}
            onChange={e => handleFileSelect(e.target.files?.[0])}
            hidden
          />
        </section>
      )}

      {step === 'preview' && (
        <section className="scr-card scr-preview">
          <div className="scr-file">
            <span className="scr-file-name" title={selectedFile?.name}>{selectedFile?.name || 'Selected dental image'}</span>
            {selectedFile?.size > 0 && <span className="scr-file-size">{formatBytes(selectedFile.size)}</span>}
          </div>

          <div className={`scr-image ${loading ? 'is-analysing' : ''}`.trim()}>
            <img src={previewUrl} alt={`Teeth selected for screening${patientName ? ` of ${patientName}` : ''}`} />
            {loading && (
              <div className="scr-scan" aria-hidden="true"><span className="scr-scan-line" /></div>
            )}
          </div>

          <p className="sr-only" role="status" aria-live="polite">
            {loading ? 'Analysing the image. This can take up to a minute.' : ''}
          </p>
          {loading && <p className="scr-analysing-text" aria-hidden="true">Analysing with the YOLOv8 + YOLOv12 ensemble… this can take up to a minute.</p>}

          <div className="scr-actions">
            <Button variant="secondary" icon={RefreshCw} onClick={resetUpload} disabled={loading}>Change image</Button>
            <Button
              icon={ScanLine}
              onClick={runDetection}
              disabled={loading || !detectionEnabled}
              aria-busy={loading}
              title={detectionEnabled ? undefined : 'AI screening is temporarily unavailable.'}
            >
              {loading ? 'Analysing…' : 'Run detection'}
            </Button>
          </div>
        </section>
      )}

      {step === 'results' && screening && (
        <section className="scr-card scr-result" aria-labelledby="scr-result-title">
          <span className="scr-result-icon" aria-hidden="true"><CheckCircle2 size={34} strokeWidth={1.8} /></span>
          <h3 id="scr-result-title" className="scr-result-title">Analysis complete</h3>
          <div className="scr-result-summary">
            {screening.risk_level && <RiskBadge level={screening.risk_level} suffix="risk" size="lg" />}
            <span className="scr-result-count">{detectionCount} finding{detectionCount !== 1 ? 's' : ''} detected</span>
          </div>
          <p className="scr-result-note">AI results are assistive. Review the findings before discussing them with the patient.</p>
          <div className="scr-actions">
            <Button variant="secondary" icon={RefreshCw} onClick={resetUpload}>Screen another image</Button>
            <Button icon={ArrowRight} iconPosition="right" onClick={() => navigate('/dashboard/screenings/' + screening.id)}>
              View detailed results
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
