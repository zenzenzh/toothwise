import React from 'react';
import PropTypes from 'prop-types';

/**
 * StatCard — a single dashboard metric.
 * `tone="danger"` highlights the icon chip for values that need attention.
 */
const StatCard = ({
  label,
  value,
  icon: Icon,
  trend,
  tone = 'default',
  className = '',
  style,
}) => (
  <div className={`tw-stat-card tw-stat-card--${tone} ${className}`.trim()} style={style}>
    {Icon && (
      <div className="tw-stat-card__icon" aria-hidden="true">
        <Icon size={20} strokeWidth={1.75} />
      </div>
    )}
    <div className="tw-stat-card__value">{value}</div>
    <div className="tw-stat-card__label">{label}</div>
    {trend && <div className="tw-stat-card__trend">{trend}</div>}
  </div>
);

StatCard.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.elementType,
  trend: PropTypes.string,
  tone: PropTypes.oneOf(['default', 'danger']),
  className: PropTypes.string,
  style: PropTypes.object,
};

export default StatCard;
