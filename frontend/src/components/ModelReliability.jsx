import { ShieldCheck } from 'lucide-react';
import Badge from './ui/Badge';
import { prettyLabel } from './DetectionCanvas';
import { EVALUATION, LOW_RELIABILITY_F1, METRICS, ROW_ORDER } from '../data/modelEvaluation';

const MODEL_NAME = { fused: 'Fused ensemble', yolov8: 'YOLOv8', yolov12: 'YOLOv12' };
const rowName = key => (key === 'any_finding' ? 'Any finding' : prettyLabel(key));
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

function ThisScreening({ k, seen, found }) {
  if (k === 'any_finding') {
    const n = found.length;
    return n ? <span className="sd-rel-yes">Yes · {n} condition{n !== 1 ? 's' : ''}</span> : <span className="sd-rel-no">No</span>;
  }
  const s = seen[k];
  if (!s) return <span className="sd-rel-no">Not found</span>;
  return <span className="sd-rel-yes">Found · {pct(s.best * 100)} <span className="sd-rel-marks">({s.count} mark{s.count !== 1 ? 's' : ''})</span></span>;
}

/**
 * Image-level evaluation of the screening on screen: for every condition,
 * what the model being viewed found in this photograph (highest confidence
 * and number of marks) next to its measured scores on the clean test set.
 * There is no dentist answer to compare with, so this shows how far each
 * result can be trusted, not whether it is right.
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
          <ShieldCheck size={15} aria-hidden="true" /> Image-level evaluation of this screening · {name}
        </h2>
        <span className="sd-rel-source">
          Scores measured on {EVALUATION.testImages.toLocaleString()} test photographs not used in training
        </span>
      </div>

      <ul className="sd-rel-found">
        {(found.length ? found : ['any_finding']).map(key => {
          const [, precision, recall, specificity, f1] = scores[key];
          const low = f1 < LOW_RELIABILITY_F1;
          const s = seen[key];
          return (
            <li key={key} className={low ? 'sd-rel-found--low' : undefined}>
              <span className="sd-rel-found-name">{key === 'any_finding' ? 'No condition found' : rowName(key)}</span>
              {low && <Badge tone="warning">Low reliability: confirm by examination</Badge>}
              <span className="sd-rel-found-text">
                {key === 'any_finding'
                  ? <>{name} found no condition in this photograph. On test photographs, it correctly left <strong>{pct(specificity)}</strong> of problem-free photographs clear, but it missed <strong>{pct(100 - recall)}</strong> of photographs that did show a problem, so a clear result still needs the dentist's examination.</>
                  : <>Marked <strong>{s.count}</strong> time{s.count !== 1 ? 's' : ''} in this photograph, with a highest confidence of <strong>{pct(s.best * 100)}</strong>. On test photographs, when {name} reports it, it is right <strong>{pct(precision)}</strong> of the time, and it finds <strong>{pct(recall)}</strong> of the photographs that show it.</>}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="sd-rel-table-wrap">
        <table className="sd-rel-table">
          <caption className="sr-only">This screening's result and the measured image-level scores of {name} per condition</caption>
          <thead>
            <tr>
              <th scope="col">Condition</th>
              <th scope="col" className="sd-rel-this">This screening</th>
              {METRICS.map(m => <th key={m} scope="col">{m}</th>)}
            </tr>
          </thead>
          <tbody>
            {ROW_ORDER.map(key => (
              <tr key={key} className={(key === 'any_finding' ? found.length : seen[key]) ? 'is-found' : undefined}>
                <th scope="row">{rowName(key)}</th>
                <td className="sd-rel-this"><ThisScreening k={key} seen={seen} found={found} /></td>
                {scores[key].map((v, i) => <td key={METRICS[i]}>{v.toFixed(1)}%</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="sd-rel-note">
        "This screening" shows the highest confidence the model gave each condition in this photograph and how many
        marks it made; "Not found" means no mark reached the system's cut-off (25%, or 50% for cavity). Confidence is
        the model's own score and does not confirm a finding. The other columns are the model's measured scores per
        photograph: precision is how often a reported finding is real, recall is how many real findings are caught.
        AI results assist the dentist and are not a final diagnosis.
      </p>
    </section>
  );
}
