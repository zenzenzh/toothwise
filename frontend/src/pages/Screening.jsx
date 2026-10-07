import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Upload, RefreshCw, ScanLine, CheckCircle2, Image as ImageIcon } from 'lucide-react';
import api, { screeningsAPI } from '../api';
import { validateImageFile } from '../utils/validation';
import toast from 'react-hot-toast';

import T from '../tokens';

const C = {
  burgundy: T.burgundy,
  rose: T.rose,
  gold: T.rosegold,
  blush: T.blush,
  white: T.white,
  muted: T.muted,
  border: T.border,
};

const CARD = {
  background: T.white,
  borderRadius: 14,
  padding: '28px',
  boxShadow: '0 2px 12px rgba(0,0,0,.08)',
  border: `1px solid ${T.border}`,
};

export default function Screening() {
  const { id: patientId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [step, setStep] = useState('upload'); // 'upload' | 'preview' | 'results'
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [screening, setScreening] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // AI inference can be switched off server-side (DETECTION_ENABLED=false)
  // e.g. when presenting without the models. The health endpoint is the
  // public source of truth for that switch.
  const [detectionEnabled, setDetectionEnabled] = useState(true);
  useEffect(() => {
    api.get('/health').then(({ data }) => {
      if (data && data.detection_enabled === false) setDetectionEnabled(false);
    }).catch(() => {});
  }, []);

  function handleFileSelect(file) {
    if (!file) return;
    const check = validateImageFile(file);
    if (!check.valid) {
      toast.error(check.message);
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onerror = () => toast.error('Unable to read this image. Please choose another file.');
    reader.onload = ev => {
      setPreviewUrl(ev.target.result);
      setStep('preview');
    };
    reader.readAsDataURL(file);
  }

  function handleFileInputChange(e) {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  }

  function resetUpload() {
    setSelectedFile(null);
    setPreviewUrl(null);
    setStep('upload');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function runDetection() {
    if (loading) return; // guard against double-submit
    if (!detectionEnabled) {
      toast.error('AI screening is temporarily unavailable.');
      return;
    }
    if (!selectedFile) {
      toast.error('Please choose an image first.');
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
      toast.success('Detection complete!');
    } catch (err) {
      toast.error(err.friendlyMessage || 'Detection failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="screening-page tw-page-layout" style={{ maxWidth: 800, margin: '0 auto' }}>
      <div>
        <button onClick={() => navigate('/dashboard/patients/' + patientId)} className="tw-secondary-action-btn">
          ← Back to Patient
        </button>
      </div>

      <div className="tw-page-title-wrap">
        <h2>New AI Screening — Patient #{patientId}</h2>
      </div>

      {step === 'upload' && (
        <div className="screening-card" style={CARD}>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{
              border: `2px dashed ${isDragging ? 'var(--tw-primary, #6B2D46)' : T.border}`,
              borderRadius: 14,
              padding: '52px 24px',
              textAlign: 'center',
              background: isDragging ? 'rgba(107, 45, 70, 0.04)' : T.blush,
              transition: 'all 0.2s ease',
              cursor: 'pointer',
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <div
              style={{
                width: 60,
                height: 60,
                borderRadius: 16,
                background: T.bg,
                display: 'grid',
                placeItems: 'center',
                margin: '0 auto 16px',
                color: C.rose,
              }}
            >
              <Upload size={28} strokeWidth={1.75} />
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: C.burgundy, marginBottom: 8 }}>
              Upload Dental Image
            </h3>
            <p style={{ color: C.muted, fontSize: 13.5, marginBottom: 20, maxWidth: 440, margin: '0 auto 20px', lineHeight: 1.5 }}>
              Drag and drop an image here or click to browse. Supports JPEG, PNG, or WebP up to 10MB.
            </p>
            <button
              type="button"
              className="tw-primary-action-btn"
              style={{ display: 'inline-flex', pointerEvents: 'none' }}
            >
              Choose Dental Image
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileInputChange}
              style={{ display: 'none' }}
            />
          </div>
        </div>
      )}

      {step === 'preview' && (
        <div style={{ ...CARD, textAlign: 'center' }}>
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <ImageIcon size={18} color={C.burgundy} />
            <span style={{ fontSize: 14, fontWeight: 600, color: C.burgundy }}>
              {selectedFile?.name || 'Selected dental image'}
            </span>
            {selectedFile?.size && (
              <span style={{ fontSize: 12, color: C.muted }}>
                ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
              </span>
            )}
          </div>

          <img
            src={previewUrl}
            alt="Selected dental specimen for screening"
            style={{ width: '100%', maxWidth: 500, borderRadius: 12, marginBottom: 20, border: `2px solid ${T.border}` }}
          />

          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={resetUpload} className="tw-secondary-action-btn">
              <RefreshCw size={15} /> Change Image
            </button>
            <button
              onClick={runDetection}
              disabled={loading || !detectionEnabled}
              title={detectionEnabled ? undefined : 'AI screening is temporarily unavailable.'}
              className="tw-primary-action-btn"
              style={{ ...(detectionEnabled ? {} : { opacity: 0.55, cursor: 'not-allowed' }) }}
            >
              {loading ? (
                <>
                  <ScanLine size={16} /> Analyzing...
                </>
              ) : (
                <>
                  <ScanLine size={16} /> Run Detection
                </>
              )}
            </button>
          </div>

          {!detectionEnabled && (
            <p style={{ color: C.muted, fontSize: 12.5, marginTop: 14 }}>
              AI screening is temporarily unavailable. The image is kept — detection can be re-enabled later.
            </p>
          )}
        </div>
      )}

      {step === 'results' && (
        <div style={{ ...CARD, textAlign: 'center', padding: '48px 24px' }}>
          <CheckCircle2 size={52} strokeWidth={1.7} aria-hidden="true" style={{ marginBottom: 12, color: T.success }} />
          <h3 style={{ color: C.burgundy, fontWeight: 700 }}>Analysis Complete</h3>
          <button onClick={() => navigate('/dashboard/screenings/' + screening.id)} className="tw-primary-action-btn" style={{ marginTop: 20 }}>
            View Detailed Results →
          </button>
        </div>
      )}
    </div>
  );
}