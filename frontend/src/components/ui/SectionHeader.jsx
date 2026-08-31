import React from 'react';
import PropTypes from 'prop-types';

/**
 * SectionHeader component following the ToothWise design system.
 */
const SectionHeader = ({
  title,
  action,
  className = '',
}) => {
  return (
    <div className={`tw-section-header ${className}`}>
      <h3 className="tw-section-header__title">{title}</h3>
      {action && <div className="tw-section-header__action">{action}</div>}
    </div>
  );
};

SectionHeader.propTypes = {
  title: PropTypes.string.isRequired,
  action: PropTypes.node,
  className: PropTypes.string,
};

export default SectionHeader;