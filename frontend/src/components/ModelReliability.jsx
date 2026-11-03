import { ShieldCheck } from 'lucide-react';
import Badge from './ui/Badge';
import { prettyLabel } from './DetectionCanvas';
import { EVALUATION, LOW_RELIABILITY_F1, METRICS, ROW_ORDER } from '../data/modelEvaluation';

const MODEL_NAME = { fused: 'Fused ensemble', yolov8: 'YOLOv8', yolov12: 'YOLOv12' };
const rowName = key => (key === 'any_finding' ? 'Any finding' : prettyLabel(key));
const pct = v => `${Math.round(v)}%`;

/**
 * How far the findings on this screen can be trusted: the measured
 * image-level scores of the model being viewed, with the conditions found
 * in this screening listed first in plain language.
 */
export default function ModelReliability({ model = 'fused', detections = [] }) {
  const scores = EVALUATION.models[model] || EVALUATION.models.fused;
  const found = ROW_ORDER.filter(k => k !== 'any_finding' && detections.some(d => d.label === k));

  return (
    <section className="sd-card sd-rel" aria-labelledby="sd-rel-title">
      <div className="sd-rel-head">
        <h2 id="sd-rel-title" className="sd-sec-title">
          <ShieldCheck size={15} aria-hidden="true" /> AI reliability · {MODEL_NAME[model] || MODEL_NAME.fused}
        </h2>
        <span className="sd-rel-source">
          Measured on {EVALUATION.testImages.toLocaleString()} test photographs not used in training
        </span>
      </div>

      <ul className="sd-rel-found">
        {(found.length ? found : ['any_finding']).map(key => {
          const [, precision, recall, specificity, f1] = scores[key];
          const low = f1 < LOW_RELIABILITY_F1;
          return (
            <li key={key} className={low ? 'sd-rel-found--low' : undefined}>
              <span className="sd-rel-found-name">{rowName(key)}</span>
              {low && <Badge tone="warning">Low reliability: confirm by examination</Badge>}
              <span className="sd-rel-found-text">
                {key === 'any_finding'
                  ? <>It finds a dental problem in <strong>{pct(recall)}</strong> of photographs that show one, and correctly leaves <strong>{pct(specificity)}</strong> of problem-free photographs clear.</>
                  : <>When this model reports it, it is right <strong>{pct(precision)}</strong> of the time, and it finds <strong>{pct(recall)}</strong> of the photographs that show it.</>}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="sd-rel-table-wrap">
        <table className="sd-rel-table">
          <caption className="sr-only">Image-level scores of {MODEL_NAME[model] || MODEL_NAME.fused} per condition</caption>
          <thead>
            <tr>
              <th scope="col">Condition</th>
              {METRICS.map(m => <th key={m} scope="col">{m}</th>)}
            </tr>
          </thead>
          <tbody>
            {ROW_ORDER.map(key => (
              <tr key={key} className={found.includes(key) ? 'is-found' : undefined}>
                <th scope="row">
                  {rowName(key)}
                  {found.includes(key) && <span className="sr-only"> (found in this screening)</span>}
                </th>
                {scores[key].map((v, i) => <td key={METRICS[i]}>{v.toFixed(1)}%</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="sd-rel-note">
        Highlighted rows are conditions found in this screening. Precision: how often a reported finding is real.
        Recall: how many real findings are caught. AI results assist the dentist and are not a final diagnosis.
      </p>
    </section>
  );
}
