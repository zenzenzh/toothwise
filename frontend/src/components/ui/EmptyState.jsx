import React from 'react';
import PropTypes from 'prop-types';

/**
 * EmptyState component following the ToothWise design system.
 * Used for lists, tables, or dashboard widgets with no data.
 */
const EmptyState = ({
  icon: Icon,
  title,
  message,
  action,
  className = '',
}) => {
  return (
    <div className={`tw-state ${className}`}>
      <div className="tw-state__icon">
        {Icon ? <Icon size={48} strokeWidth={1.5} /> : '🔍'}
      </div>
      <h3 className="tw-state__title">{title || 'No data available'}</h3>
      <p className="tw-state__text">{message || 'There is nothing to display at the moment.'}</p>
      {action && <div className="tw-state__action">{action}</div>}
    </div>
  );
};

EmptyState.propTypes = {
  icon: PropTypes.elementType,
  title: PropTypes.string,
  message: PropTypes.string,
  action: PropTypes.node,
  className: PropTypes.string,
};

export default EmptyState;
