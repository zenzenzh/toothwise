import React from 'react';
import PropTypes from 'prop-types';

/**
 * StatCard component following the ToothWise design system.
 * Used for dashboard metrics.
 */
const StatCard = ({
  label,
  value,
  icon: Icon,
  trend,
  color = 'var(--tw-burgundy)',
  className = '',
}) => {
  return (
    <div className={`tw-card tw-hover-lift stagger-item ${className}`} style={{ borderTop: `4px solid ${color}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--tw-space-3)' }}>
        <div style={{
          width: 40, height: 40, borderRadius: 'var(--tw-radius-md)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--tw-white)', border: '1.5px solid var(--tw-border)'
        }}>
          {Icon && <Icon size={20} strokeWidth={1.75} color="var(--tw-ink)" />}
        </div>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
      </div>
      <div style={{ fontSize: '32px', fontWeight: '700', lineHeight: 1, color }}>
        {value}
      </div>
      <div style={{ fontSize: 'var(--tw-text-label)', color: 'var(--tw-muted)', fontWeight: '500', marginTop: 'var(--tw-space-1)' }}>
        {label}
      </div>
      {trend && (
        <div style={{ marginTop: 'var(--tw-space-3)', fontSize: 'var(--tw-text-caption)', color: 'var(--tw-success)' }}>
          {trend}
        </div>
      )}
    </div>
  );
};

StatCard.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  icon: PropTypes.elementType,
  trend: PropTypes.string,
  color: PropTypes.string,
  className: PropTypes.string,
};

export default StatCard;