import React from 'react';
import PropTypes from 'prop-types';

// API risk levels → CSS modifier. MEDIUM is shown as "Moderate" nowhere in
// the API, so keep the label as-is and only normalise the class.
const TONE = { HIGH: 'high', MEDIUM: 'medium', MODERATE: 'medium', LOW: 'low' };

/**
 * RiskBadge — the one place risk levels get their colour, so HIGH / MEDIUM /
 * LOW read the same on every staff and patient screen, in both themes.
 */
const RiskBadge = ({ level, suffix, size = 'md', className = '' }) => {
  if (!level) return null;
  const key = String(level).toUpperCase();
  return (
    <span className={`tw-risk tw-risk--${TONE[key] || 'low'} tw-risk--${size} ${className}`.trim()}>
      {key}{suffix ? ` ${suffix}` : ''}
    </span>
  );
};

RiskBadge.propTypes = {
  level: PropTypes.string,
  suffix: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  className: PropTypes.string,
};

export const RISK_COLOR = {
  HIGH: 'var(--tw-danger)',
  MEDIUM: 'var(--tw-warning)',
  LOW: 'var(--tw-success)',
};

export default RiskBadge;
