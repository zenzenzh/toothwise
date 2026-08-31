// Local Q&A engine for the patient-portal "Screening Assistant".
//
// Why this exists as a separate, offline-only module: the clinic-wide
// ChatWidget (see components/ChatWidget.jsx, api/chatbot.js) deliberately
// never sees a patient's real screening data - it's built on the free
// Gemini tier, whose provider may use submitted content to improve its
// products, so it explicitly refuses "what did my screening find?" style
// questions and points the patient back to the portal.
//
// This module IS the answer to that redirect. It runs entirely in the
// browser against data the patient is already authenticated to see
// (fetched via patientScreeningsAPI, same as the Screening History tab)
// and never sends any of it to a network request. If it doesn't recognize
// the question, it returns null so the caller can fall back to the
// general clinic assistant for non-personal dental questions instead of
// guessing at an answer.

const LABEL_INFO = {
  healthy_tooth: {
    name: 'healthy tooth',
    blurb: 'no issues were seen on that tooth',
  },
  cavity: {
    name: 'cavity',
    blurb: 'a decayed area that usually needs a filling before it grows larger',
  },
  gum_inflammation: {
    name: 'gum inflammation',
    blurb: 'redness or swelling of the gums, which usually improves with a professional cleaning and better home care',
  },
  plaque: {
    name: 'plaque',
    blurb: 'the soft, sticky film of bacteria that forms daily on teeth - regular brushing and flossing clears it',
  },
  tartar: {
    name: 'tartar (calculus)',
    blurb: 'hardened plaque that brushing alone can no longer remove, so it needs a professional cleaning',
  },
};

const LABEL_SYNONYMS = {
  cavity: 'cavity', cavities: 'cavity', decay: 'cavity', caries: 'cavity',
  gum: 'gum_inflammation', gums: 'gum_inflammation', gingivitis: 'gum_inflammation', 'gum inflammation': 'gum_inflammation', 'gum disease': 'gum_inflammation',
  plaque: 'plaque',
  tartar: 'tartar', calculus: 'tartar',
  healthy: 'healthy_tooth',
};

const RISK_INFO = {
  HIGH: 'means the screening picked up findings that usually need prompt attention, like a cavity, a cracked tooth, or noticeable gum inflammation.',
  MEDIUM: 'means the screening found some early wear, like plaque or tartar buildup, worth addressing at a routine cleaning.',
  LOW: 'means your teeth looked healthy in that screening, with nothing significant flagged.',
};

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleDateString('en-PH', { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'Asia/Manila' });
  } catch {
    return iso;
  }
}

function groupDetections(detections = []) {
  const counts = {};
  detections.forEach(d => {
    const key = d.label in LABEL_INFO ? d.label : d.label;
    counts[key] = (counts[key] || 0) + 1;
  });
  return counts;
}

function describeFindings(screening) {
  const counts = groupDetections(screening.detections);
  const nonHealthy = Object.entries(counts).filter(([label]) => label !== 'healthy_tooth');
  if (nonHealthy.length === 0) {
    return 'Nothing concerning was flagged in that screening - everything detected looked like a healthy tooth.';
  }
  const parts = nonHealthy.map(([label, count]) => {
    const info = LABEL_INFO[label];
    const name = info ? info.name : label.replace(/_/g, ' ');
    return `${count} ${count === 1 ? 'area' : 'areas'} of ${name}`;
  });
  return `That screening flagged ${parts.join(', ')}.`;
}

function latestRiskTrendNote(screenings) {
  if (screenings.length < 2) return '';
  const order = { LOW: 0, MEDIUM: 1, HIGH: 2 };
  const [latest, previous] = screenings;
  if (order[latest.risk_level] > order[previous.risk_level]) {
    return " That's higher than your previous screening, so it's worth booking a visit soon.";
  }
  if (order[latest.risk_level] < order[previous.risk_level]) {
    return ' That\'s an improvement from your previous screening - nice work.';
  }
  return ' That\'s about the same as your previous screening.';
}

function findLabelMention(lowerText) {
  for (const [word, label] of Object.entries(LABEL_SYNONYMS)) {
    if (lowerText.includes(word)) return label;
  }
  return null;
}

/**
 * Attempts to answer `question` using the patient's own already-fetched
 * `screenings` (newest first, same shape as patientScreeningsAPI.mine()).
 * Returns a string answer, or null if the question isn't recognized as a
 * screening/results question (caller should fall back elsewhere).
 */
export function answerPatientQuestion(question, screenings = []) {
  const q = question.trim().toLowerCase();
  if (!q) return null;

  const hasScreenings = screenings.length > 0;
  const latest = screenings[0];

  // General risk-level explainer works even with no screenings on file yet.
  if (/what (does|do)\s+(a\s+)?(high|medium|low)\s*risk\s*(level|mean)/.test(q) || /(high|medium|low)\s*risk\s*mean/.test(q)) {
    const level = /high/.test(q) ? 'HIGH' : /medium/.test(q) ? 'MEDIUM' : 'LOW';
    return `${level} risk ${RISK_INFO[level]}`;
  }

  const asksAboutOwnScreening = /\b(my|i|me)\b/.test(q) && /(screen|scan|result|risk|cavity|cavities|gum|plaque|tartar|crack|discolor|missing tooth|detect|finding|checkup|dental record)/.test(q);
  const asksScreeningGeneric = /(screening|screenings|scan results?|checkup results?)/.test(q) && !asksAboutOwnScreening;

  if (!asksAboutOwnScreening && !asksScreeningGeneric) return null;

  if (!hasScreenings) {
    return "You don't have any screenings on file yet - your dentist will add one after your next visit.";
  }

  // How many screenings.
  if (/how many (screenings|scans|checkups|visits|times)/.test(q) || /number of screenings/.test(q)) {
    return `You have ${screenings.length} screening${screenings.length === 1 ? '' : 's'} on file. The most recent one was on ${formatDate(latest.created_at)}.`;
  }

  // Last / latest screening date.
  if (/(last|latest|recent|most recent)\s+(screening|scan|checkup|visit)/.test(q) || /when was my last/.test(q)) {
    return `Your most recent screening was on ${formatDate(latest.created_at)}, and it came back ${latest.risk_level} risk.`;
  }

  // Risk level / how risky am I.
  if (/(my )?risk level/.test(q) || /how risky/.test(q) || /am i at risk/.test(q) || /what.?s my risk/.test(q)) {
    return `Your most recent screening (${formatDate(latest.created_at)}) came back ${latest.risk_level} risk - that ${RISK_INFO[latest.risk_level]}${latestRiskTrendNote(screenings)}`;
  }

  // What did it find / results / findings.
  if (/what (did|does)\s+(you|it|my screening|my scan)\s*find/.test(q) || /what was found/.test(q) || /(results|findings) of my/.test(q) || /what.*detect/.test(q)) {
    return `${describeFindings(latest)} (Screening from ${formatDate(latest.created_at)}, ${latest.risk_level} risk.)`;
  }

  // Recommendations / advice / next steps.
  if (/(recommend|advice|what should i do|next steps?|what.*i do next)/.test(q)) {
    if (latest.recommendations?.length > 0) {
      const list = [...latest.recommendations].sort((a, b) => a.order_index - b.order_index).map(r => `• ${r.text}`).join('\n');
      return `Based on your most recent screening (${formatDate(latest.created_at)}):\n${list}`;
    }
    return `Your most recent screening (${formatDate(latest.created_at)}) didn't include specific recommendations - keep up regular brushing, flossing, and a routine cleaning every 6 months.`;
  }

  // A specific condition mentioned by name (cavity, gum, plaque, etc.).
  const label = findLabelMention(q);
  if (label && label !== 'healthy_tooth') {
    const info = LABEL_INFO[label];
    const seenIn = screenings.filter(sc => (sc.detections || []).some(d => d.label === label));
    if (seenIn.length === 0) {
      return `Good news - ${info.name} hasn't shown up in any of your screenings on file. For reference, ${info.name} is ${info.blurb}.`;
    }
    const mostRecent = seenIn[0];
    return `${info.name.charAt(0).toUpperCase() + info.name.slice(1)} was flagged in your screening from ${formatDate(mostRecent.created_at)}. For reference, that's ${info.blurb}.`;
  }

  // Recognized as a screening question but didn't match a specific intent -
  // point them at what this assistant can do rather than guessing.
  return "I can tell you about your screening dates, risk levels, findings, and recommendations - try asking things like \"what did my last screening find?\" or \"what should I do next?\"";
}
