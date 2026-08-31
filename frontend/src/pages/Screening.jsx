import { useState, useRef, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import { Upload, Camera, RefreshCw, Flashlight, Lightbulb, ScanLine, CheckCircle2, Radio } from 'lucide-react';
import api, { screeningsAPI } from '../api';
import { validateImageFile } from '../utils/validation';
import toast from 'react-hot-toast';

const C = { 
  burgundy: '#4B2F35', 
  rose: '#BA7976', 
  gold: '#C78C8A', 
  blush: '#FBF7F5', 
  white: '#FFFFFF', 
  muted: '#6F5B61',
  border: '#E5DADC'
};

const CARD = { background: '#FFFFFF', borderRadius: 14, padding: '24px', boxShadow: '0 2px 12px rgba(92,58,74,0.07)', border: '1px solid #FBF7F5' };

export default function Screening() {
  const { id: patientId } = useParams();
  const navigate = useNavigate();
  const webcamRef = useRef(null);
  const [step, setStep] = useState('capture'); 
  const [capturedImg, setCapturedImg] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [screening, setScreening] = useState(null);
  const [loading, setLoading] = useState(false);
  const [useCamera, setUseCamera] = useState(false);
  const [facingMode, setFacingMode] = useState('environment'); 
  const [torch, setTorch] = useState(false); // NEW: Torch State

  // --- Live preview (throttled detection loop while aiming the camera) ---
  const [livePreview, setLivePreview] = useState(false);
  const [liveDetections, setLiveDetections] = useState([]);
  const [liveStatus, setLiveStatus] = useState('idle'); // idle | scanning | ok | error
  const liveBusyRef = useRef(false);
  const liveAbortRef = useRef(null);

  // AI inference can be switched off server-side (DETECTION_ENABLED=false)
  // e.g. when presenting without the models. The health endpoint is the
  // public source of truth for that switch.
  const [detectionEnabled, setDetectionEnabled] = useState(true);
  useEffect(() => {
    api.get('/health').then(({ data }) => {
      if (data && data.detection_enabled === false) setDetectionEnabled(false);
    }).catch(() => {});
  }, []);

  // Toggle Physical Flashlight
  const toggleTorch = useCallback(async () => {
    const newTorchState = !torch;
    setTorch(newTorchState);

    const stream = webcamRef.current?.video?.srcObject;
    if (stream) {
      const track = stream.getVideoTracks()[0];
      const capabilities = track.getCapabilities();
      
      if (capabilities.torch) {
        try {
          await track.applyConstraints({
            advanced: [{ torch: newTorchState }]
          });
        } catch (err) {
          // Some devices do not expose torch control; leave the camera usable.
        }
      } else {
        toast.error("Flash is not supported on this camera.");
        setTorch(false);
      }
    }
  }, [torch]);

  const capture = useCallback(() => {
    const img = webcamRef.current?.getScreenshot();
    if (img) { 
      setCapturedImg(img); 
      setUploadedFile(null); 
      setStep('preview'); 
      // Turn off torch after capture to save battery
      if (torch) toggleTorch(); 
    }
  }, [torch, toggleTorch]);

  // Grabs one downscaled frame from the live video, POSTs it to the
  // preview endpoint (see screeningsAPI.preview - nothing here is saved
  // as a screening), and updates the overlay. Skips a tick if the
  // previous request hasn't resolved yet, so a slow network/model can't
  // pile up overlapping requests.
  const runLiveFrame = useCallback(async () => {
    if (liveBusyRef.current) return;
    const shot = webcamRef.current?.getScreenshot({ width: 480 });
    if (!shot) return;
    liveBusyRef.current = true;
    setLiveStatus('scanning');
    try {
      const blob = await fetch(shot).then(r => r.blob());
      const controller = new AbortController();
      liveAbortRef.current = controller;
      const { data } = await screeningsAPI.preview(patientId, blob, controller.signal);
      setLiveDetections(data.detections || []);
      setLiveStatus('ok');
    } catch (err) {
      if (err.code !== 'ERR_CANCELED') setLiveStatus('error');
    } finally {
      liveBusyRef.current = false;
    }
  }, [patientId]);

  useEffect(() => {
    if (!(useCamera && livePreview && step === 'capture')) {
      setLiveDetections([]);
      setLiveStatus('idle');
      return undefined;
    }
    const timer = setInterval(runLiveFrame, 1500);
    return () => {
      clearInterval(timer);
      liveAbortRef.current?.abort();
    };
  }, [useCamera, livePreview, step, runLiveFrame]);

  function flipCamera() {
    setTorch(false);
    setFacingMode(prev => prev === 'environment' ? 'user' : 'environment');
  }

  function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const check = validateImageFile(file);
    if (!check.valid) {
      toast.error(check.message);
      e.target.value = ''; // allow re-selecting the same (now-fixed) filename
      return;
    }
    setUploadedFile(file);
    const reader = new FileReader();
    reader.onerror = () => toast.error('Unable to read this image. Please choose another file.');
    reader.onload = ev => { setCapturedImg(ev.target.result); setStep('preview'); };
    reader.readAsDataURL(file);
  }

  async function runDetection() {
    if (loading) return; // guard against double-submit
    if (!detectionEnabled) {
      toast.error('AI screening is temporarily unavailable.');
      return;
    }
    setLoading(true);
    try {
      let file = uploadedFile;
      if (!file && capturedImg) {
        const blob = await fetch(capturedImg).then(r => r.blob());
        file = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
      }
      const check = validateImageFile(file);
      if (!check.valid) {
        toast.error(check.message);
        return;
      }
      // Single request: backend creates the screening AND runs the
      // YOLOv8/YOLOv12 ensemble + risk scoring + KNN recommendations
      // synchronously, returning the full result.
      const { data: result } = await screeningsAPI.create(patientId, file);
      setScreening(result);
      setStep('results');
      toast.success('Detection complete!');
    } catch (err) {
      toast.error(err.friendlyMessage || 'Detection failed. Please try again.');
    } finally { setLoading(false); }
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

      {step === 'capture' && (
        <div className="screening-card" style={CARD}>
          <div className="screening-mode-toggle">
            <button
              onClick={() => { setUseCamera(false); setCapturedImg(null); setLivePreview(false); }}
              className={!useCamera ? 'tw-primary-action-btn' : 'tw-secondary-action-btn'}>
              <Upload size={16} /> Upload Image
            </button>
            <button
              onClick={() => { setUseCamera(true); setCapturedImg(null); }}
              className={useCamera ? 'tw-primary-action-btn' : 'tw-secondary-action-btn'}>
              <Camera size={16} /> Live Camera
            </button>
          </div>

          {useCamera ? (
            <div style={{ textAlign: 'center' }}>
              <div className="screening-camera-frame" style={{ position: 'relative', display: 'inline-block', width: '100%', maxWidth: 500 }}>
                <Webcam
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  screenshotQuality={1.0}
                  videoConstraints={{ facingMode: { exact: facingMode } }}
                  style={{ 
                    width: '100%', 
                    borderRadius: 12, 
                    border: `4px solid ${C.blush}`,
                    display: 'block',
                    // Apply a software "Flash" filter if torch is on
                    filter: torch ? 'brightness(1.1) contrast(1.1)' : 'none'
                  }}
                />
                {livePreview && (
                  <div style={{ position: 'absolute', inset: 4, pointerEvents: 'none', borderRadius: 8, overflow: 'hidden' }}>
                    {liveDetections.map((d, i) => (
                      <div key={i} style={{
                        position: 'absolute',
                        left: `${d.x1 * 100}%`, top: `${d.y1 * 100}%`,
                        width: `${Math.max(d.x2 - d.x1, 0.01) * 100}%`, height: `${Math.max(d.y2 - d.y1, 0.01) * 100}%`,
                        border: `2px solid ${d.label === 'healthy_tooth' ? '#4CAF82' : '#EAB308'}`,
                        borderRadius: 4,
                        boxShadow: '0 0 0 1px rgba(0,0,0,.3)',
                      }}>
                        <span style={{
                          position: 'absolute', top: -19, left: -2,
                          background: d.label === 'healthy_tooth' ? '#4CAF82' : '#EAB308',
                          color: d.label === 'healthy_tooth' ? '#fff' : '#241A1E',
                          fontSize: 10, fontWeight: 800, padding: '2px 6px', borderRadius: 5,
                          whiteSpace: 'nowrap',
                        }}>
                          {d.label.replace(/_/g, ' ')} {(d.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                    <div style={{
                      position: 'absolute', bottom: 8, left: 8,
                      display: 'flex', alignItems: 'center', gap: 6,
                      background: 'rgba(36,26,30,.6)', color: '#fff', fontSize: 10, fontWeight: 700,
                      padding: '4px 9px', borderRadius: 20, backdropFilter: 'blur(3px)',
                    }}>
                      <Radio size={11} style={{ opacity: liveStatus === 'scanning' ? 1 : 0.5 }} />
                      {liveStatus === 'scanning' ? 'Scanning…' : liveStatus === 'error' ? 'Preview paused (connection issue)' : 'Live preview'}
                    </div>
                  </div>
                )}
              </div>

              <div className="screening-controls">
                <button onClick={flipCamera} className="tw-secondary-action-btn">
                  <RefreshCw size={15} /> Flip
                </button>

                {/* FLASH BUTTON */}
                <button 
                  onClick={toggleTorch} 
                  className="tw-secondary-action-btn"
                  style={{ 
                    background: torch ? '#EAB308' : 'rgba(92,58,74,0.08)', 
                    color: torch ? '#000' : C.burgundy,
                    borderColor: torch ? '#EAB308' : C.border
                  }}>
                  {torch ? <><Flashlight size={15} /> Flash On</> : <><Lightbulb size={15} /> Flash Off</>}
                </button>

                {detectionEnabled && (
                  <button
                    onClick={() => setLivePreview(v => !v)}
                    className="tw-secondary-action-btn"
                    style={{
                      background: livePreview ? '#4CAF82' : 'rgba(92,58,74,0.08)',
                      color: livePreview ? '#fff' : C.burgundy,
                      borderColor: livePreview ? '#4CAF82' : C.border,
                    }}>
                    <Radio size={15} /> {livePreview ? 'Live: On' : 'Live: Off'}
                  </button>
                )}

                <button onClick={capture} className="tw-primary-action-btn">
                  <Camera size={16} /> Capture
                </button>
              </div>
              <p style={{ color: C.muted, fontSize: 11.5, marginTop: 12, lineHeight: 1.5 }}>
                {detectionEnabled
                  ? <>Live Detection shows a running preview of likely findings while you aim the camera —
                    it isn't saved. Click Capture when you're ready to run the full screening and save the result.</>
                  : 'AI detection is temporarily unavailable — capture is still available and nothing will be analyzed.'}
              </p>
            </div>
          ) : (
            <div style={{ border: `2px dashed ${C.border}`, borderRadius: 14, padding: '48px 20px', textAlign: 'center', background: C.blush }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🦷</div>
              <p style={{ color: C.muted, fontSize: 14, marginBottom: 20 }}>
                Upload an intraoral dental image for analysis
              </p>
              <label className="tw-primary-action-btn" style={{ display: 'inline-flex', cursor: 'pointer' }}>
                Choose Image
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleFileUpload} style={{ display: 'none' }} />
              </label>
            </div>
          )}
        </div>
      )}

      {step === 'preview' && (
        <div style={{ ...CARD, textAlign: 'center' }}>
          <img src={capturedImg} alt="preview" style={{ width: '100%', maxWidth: 500, borderRadius: 12, marginBottom: 20, border: `4px solid ${C.blush}` }} />
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button onClick={() => setStep('capture')} className="tw-secondary-action-btn"><RefreshCw size={15} /> Retake</button>
            <button
              onClick={runDetection}
              disabled={loading || !detectionEnabled}
              title={detectionEnabled ? undefined : 'AI screening is temporarily unavailable.'}
              className="tw-primary-action-btn"
              style={{ ...(detectionEnabled ? {} : { opacity: 0.55, cursor: 'not-allowed' }) }}>
              {loading ? <><ScanLine size={16} /> Analyzing...</> : <><ScanLine size={16} /> Run Detection</>}
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
          <CheckCircle2 size={52} strokeWidth={1.7} aria-hidden="true" style={{ marginBottom: 12, color: '#2CCB91' }} />
          <h3 style={{ color: C.burgundy, fontWeight: 700 }}>Analysis Complete</h3>
          <button onClick={() => navigate('/dashboard/screenings/' + screening.id)} className="tw-primary-action-btn" style={{ marginTop: 20 }}>
            View Detailed Results →
          </button>
        </div>
      )}
    </div>
  );
}