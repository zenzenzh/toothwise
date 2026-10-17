import React from 'react';
import PropTypes from 'prop-types';
import { Search } from 'lucide-react';

/**
 * EmptyState — also used for error states (pass `role="alert"` and an
 * action such as a Retry button). `compact` fits inside cards.
 */
const EmptyState = ({
  icon: Icon = Search,
  title,
  message,
  action,
  compact = false,
  className = '',
  ...props
}) => (
  <div className={`tw-state ${compact ? 'tw-state--compact' : ''} ${className}`.trim()} {...props}>
    <div className="tw-state__icon" aria-hidden="true">
      <Icon size={compact ? 22 : 26} strokeWidth={1.75} />
    </div>
    <h3 className="tw-state__title">{title || 'No data available'}</h3>
    {message !== null && (
      <p className="tw-state__text">{message || 'There is nothing to display at the moment.'}</p>
    )}
    {action && <div className="tw-state__action">{action}</div>}
  </div>
);

EmptyState.propTypes = {
  icon: PropTypes.elementType,
  title: PropTypes.string,
  message: PropTypes.string,
  action: PropTypes.node,
  compact: PropTypes.bool,
  className: PropTypes.string,
};

export default EmptyState;
