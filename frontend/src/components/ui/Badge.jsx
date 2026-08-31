import React from 'react';
import PropTypes from 'prop-types';

/**
 * Badge component following the ToothWise design system.
 * Uses semantic classes for risk levels and status.
 */
const Badge = ({
  children,
  className = '',
  variant = 'default',
  ...props
}) => {
  const variantClasses = {
    default: 'tw-badge',
    high: 'risk-high',
    moderate: 'risk-moderate',
    medium: 'risk-moderate',
    low: 'risk-low',
    scheduled: 'status-scheduled',
    completed: 'status-completed',
    cancelled: 'status-cancelled',
    no_show: 'status-no_show',
    active: 'status-active',
    inactive: 'status-inactive',
    admin: 'status-role-admin',
    dentist: 'status-role-dentist',
  };

  const combinedClassName = `tw-badge ${variantClasses[variant] || ''} ${className}`.trim();

  return (
    <span className={combinedClassName} {...props}>
      {children}
    </span>
  );
};

Badge.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  variant: PropTypes.string,
};

export default Badge;
