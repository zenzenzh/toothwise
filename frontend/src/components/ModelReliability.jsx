import { ShieldCheck } from 'lucide-react';
import Badge from './ui/Badge';
import { prettyLabel } from './DetectionCanvas';
import { EVALUATION, LOW_RELIABILITY_F1, METRICS, ROW_ORDER } from '../data/modelEvaluation';

const MODEL_NAME = { fused: 'Fused ensemble', yolov8: 'YOLOv8', yolov12: 'YOLOv12' };
const pct = v => `${Math.round(v)}%`;

// Per condition in this screening: number of marks and the highest confidence.
function summarize(detections) {
  const out = {};
  for (const d of detections) {
    const s = out[d.label] || (out[d.label] = { count: 0, best: 0 });
    s.count += 1;
    s.best = Math.max(s.best, d.confidence);
  }
  return out;
}

/**
 * Image-level evaluation of the screening on screen: each condition the
 * model being viewed detected, with its highest confidence and number of
 * marks, next to that model's measured per-photograph scores on the clean
 * test set. Shows how far each result can be trusted, not whether it is right.
 */
export default function ModelReliability({ model = 'fused', detections = [] }) {
  const scores = EVALUATION.models[model] || EVALUATION.models.fused;
  const name = MODEL_NAME[model] || MODEL_NAME.fused;
  const seen = summarize(detections);
  const found = ROW_ORDER.filter(k => k !== 'any_finding' && seen[k]);

  return (
    <section className="sd-card sd-rel" aria-labelledby="sd-rel-title">
      <div className="sd-rel-head">
        <h2 id="sd-rel-title" className="sd-sec-title">
          <ShieldCheck size={15} aria-hidden="true" /> Detected conditions and image-level evaluation · {name}
        </h2>
        <span className="sd-rel-source">
          Scores measured on {EVALUATION.testImages.toLocaleString()} test photographs not used in training
        </span>
      </div>

      <div className="sd-rel-table-wrap">
        <table className="sd-rel-table">
          <caption className="sr-only">Conditions {name} detected in this screening and its measured image-level scores</caption>
          <thead>
            <tr>
              <th scope="col">Detected condition</th>
              <th scope="col" className="sd-rel-this">In this photograph</th>
              {METRICS.map(m => <th key={m} scope="col">{m}</th>)}
            </tr>
          </thead>
          <tbody>
            {found.length ? found.map(key => (
              <tr key={key}>
                <th scope="row">
                  {prettyLabel(key)}
                  {scores[key][4] < LOW_RELIABILITY_F1 && (
                    <Badge tone="warning" className="sd-rel-low">Low reliability: confirm by examination</Badge>
                  )}
                </th>
                <td className="sd-rel-this">
                  <span className="sd-rel-yes">{pct(seen[key].best * 100)} confidence</span>{' '}
                  <span className="sd-rel-marks">({seen[key].count} mark{seen[key].count !== 1 ? 's' : ''})</span>
                </td>
                {scores[key].map((v, i) => <td key={METRICS[i]}>{v.toFixed(1)}%</td>)}
              </tr>
            )) : (
              <tr>
                <th scope="row">None detected</th>
                <td className="sd-rel-this sd-rel-no">No condition reached the cut-off</td>
                {scores.any_finding.map((v, i) => <td key={METRICS[i]}>{v.toFixed(1)}%</td>)}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="sd-rel-note">
        {found.length
          ? 'Scores are for each detected condition. Confidence is the model\'s own score and does not confirm a finding.'
          : `Scores are for detecting any condition. ${name} misses ${pct(100 - scores.any_finding[2])} of photographs that show a problem, so a clear result still needs the dentist's examination.`}
        {' '}AI results assist the dentist and are not a final diagnosis.
      </p>
    </section>
  );
}
