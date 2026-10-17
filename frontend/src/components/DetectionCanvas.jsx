import { useEffect, useRef, useState } from 'react';

// Matches app/ml/labels.py LABELS on the backend. Canvas drawing needs
// literal colours, so these stay hex rather than CSS variables.
export const CLASS_COLORS = {
  healthy_tooth:       '#22C55E',
  cavity:              '#EF4444',
  gum_inflammation:    '#F97316',
  plaque:              '#EAB308',
  tartar:              '#B45309',
};
// Deeper variants for the patient portal, where labels sit on photos at
// small sizes and white text needs more contrast.
export const CLASS_COLORS_DEEP = {
  healthy_tooth:       '#166534',
  cavity:              '#B91C1C',
  gum_inflammation:    '#C2410C',
  plaque:              '#A16207',
  tartar:              '#92400E',
};
export const FALLBACK_COLOR = '#8B5CF6';

export const prettyLabel = label => String(label).replace(/_/g, ' ');

export function describeDetections(detections) {
  if (!detections?.length) return 'No findings were detected.';
  const counts = detections.reduce((acc, d) => ({ ...acc, [d.label]: (acc[d.label] || 0) + 1 }), {});
  return Object.entries(counts).map(([l, n]) => `${n} ${prettyLabel(l)}`).join(', ');
}

/**
 * DetectionCanvas — draws a screening image with its detection boxes.
 * Shows a shimmer while the image decodes; the canvas carries a text
 * summary of the findings for screen readers.
 */
export default function DetectionCanvas({ imageUrl, detections, showBoxes = true, colors = CLASS_COLORS, className = '' }) {
  const canvasRef = useRef(null);
  const [imgLoaded, setImgLoaded] = useState(false);

  useEffect(() => {
    if (!imageUrl || !detections) return undefined;
    let cancelled = false;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
      if (cancelled) return;
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

          const color = colors[d.label] || FALLBACK_COLOR;
          ctx.strokeStyle = color;
          ctx.lineWidth = Math.max(4, img.naturalWidth / 200);
          ctx.strokeRect(x, y, w, h);

          const label = `${prettyLabel(d.label)} ${(d.confidence * 100).toFixed(0)}%`;
          const fontSize = Math.max(14, img.naturalWidth / 40);
          const tagH = fontSize + 10;
          ctx.font = `bold ${fontSize}px system-ui, sans-serif`;
          const textW = ctx.measureText(label).width;

          // Boxes touching the top/right edge keep their tag on-canvas.
          const tagY = y - tagH >= 0 ? y - tagH : y;
          const tagX = Math.max(0, Math.min(x, img.naturalWidth - textW - 10));
          ctx.fillStyle = color;
          ctx.fillRect(tagX, tagY, textW + 10, tagH);
          ctx.fillStyle = '#FFFFFF';
          ctx.fillText(label, tagX + 5, tagY + fontSize + 2);
        });
      }
      setImgLoaded(true);
    };
    img.src = imageUrl;
    return () => { cancelled = true; };
  }, [imageUrl, detections, showBoxes, colors]);

  return (
    <div className={`tw-detect ${className}`.trim()}>
      {!imgLoaded && <div className="tw-detect-loading skeleton" aria-hidden="true" />}
      <canvas
        ref={canvasRef}
        className="tw-detect-canvas"
        style={{ display: imgLoaded ? 'block' : 'none' }}
        role="img"
        aria-label={`Dental screening with detected findings: ${describeDetections(detections)}`}
      />
    </div>
  );
}
