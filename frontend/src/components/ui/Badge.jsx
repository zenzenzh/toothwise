import React from 'react';
import PropTypes from 'prop-types';

/**
 * Badge.
 *  - `tone` (neutral | accent | success | warning | danger | info) renders a
 *    soft, sentence-case pill — use for roles, statuses and tags.
 *  - `variant` keeps the legacy uppercase risk/status badges (risk-high, …).
 */
const LEGACY = {
  high: 'risk-high', HIGH: 'risk-high',
  moderate: 'risk-moderate', medium: 'risk-moderate', MEDIUM: 'risk-moderate',
  low: 'risk-low', LOW: 'risk-low',
};

const Badge = ({ children, className = '', variant, tone, dot = false, ...props }) => {
  const cls = tone
    ? `tw-pill tw-pill--${tone}`
    : `tw-badge ${LEGACY[variant] || ''}`;
  return (
    <span className={`${cls} ${className}`.replace(/\s+/g, ' ').trim()} {...props}>
      {dot && <span className="tw-pill__dot" aria-hidden="true" />}
      {children}
    </span>
  );
};

Badge.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  variant: PropTypes.string,
  tone: PropTypes.oneOf(['neutral', 'accent', 'success', 'warning', 'danger', 'info']),
  dot: PropTypes.bool,
};

export default Badge;
