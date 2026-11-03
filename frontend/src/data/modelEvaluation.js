// Image-level evaluation of the detection models, shown on the screening
// results page so staff can see how far each finding can be trusted.
//
// Source: backend/training/evaluate_image_level.py, "deployed" thresholds
// (0.25, cavity 0.50, applied per model before fusion; the fused result keeps
// a cavity only when both models found it), on the 2,081 test photographs
// left after check_test_leakage.py removed copies of training/validation
// photographs. These are the settings the live system uses, so the numbers
// describe what this page shows. The braces filter is not included.
// Reported in Chapter IV of the paper (Table 20 and Section 4.1).
//
// Re-run the evaluation and update these numbers whenever the weights,
// thresholds, or fusion rules change.

export const EVALUATION = {
  testImages: 2081,
  // Per model: condition -> [accuracy, precision, recall, specificity, F1], in %.
  models: {
    fused: {
      any_finding: [82.8, 92.5, 76.5, 91.4, 83.7],
      cavity: [86.4, 93.1, 71.9, 96.3, 81.1],
      tartar: [92.5, 79.6, 73.3, 96.3, 76.3],
      gum_inflammation: [95.9, 49.5, 56.0, 97.6, 52.5],
      plaque: [95.5, 57.1, 16.3, 99.4, 25.4],
      healthy_tooth: [97.7, 41.3, 91.2, 97.9, 56.9],
    },
    yolov8: {
      any_finding: [83.6, 92.4, 78.0, 91.2, 84.6],
      cavity: [87.7, 90.7, 77.9, 94.5, 83.8],
      tartar: [92.6, 83.9, 68.1, 97.4, 75.2],
      gum_inflammation: [96.7, 59.7, 54.8, 98.4, 57.1],
      plaque: [95.3, 52.4, 11.2, 99.5, 18.5],
      healthy_tooth: [98.3, 48.3, 85.3, 98.5, 61.7],
    },
    yolov12: {
      any_finding: [82.4, 91.9, 76.2, 90.8, 83.3],
      cavity: [87.0, 89.8, 76.9, 94.0, 82.9],
      tartar: [91.9, 83.1, 64.3, 97.4, 72.5],
      gum_inflammation: [95.6, 44.4, 38.1, 98.0, 41.0],
      plaque: [95.3, 52.4, 11.2, 99.5, 18.5],
      healthy_tooth: [98.4, 50.0, 82.4, 98.6, 62.2],
    },
  },
};

// Below this F1-score a finding is flagged as low reliability.
export const LOW_RELIABILITY_F1 = 60;

export const METRICS = ['Accuracy', 'Precision', 'Recall', 'Specificity', 'F1-score'];

export const ROW_ORDER = ['any_finding', 'cavity', 'tartar', 'gum_inflammation', 'plaque', 'healthy_tooth'];
