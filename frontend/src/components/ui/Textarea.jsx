import React from 'react';
import PropTypes from 'prop-types';

/**
 * Textarea component following the ToothWise design system.
 */
const Textarea = ({
  className = '',
  rows = 4,
  ...props
}) => {
  return (
    <textarea
      className={`tw-textarea ${className}`}
      rows={rows}
      {...props}
    />
  );
};

Textarea.propTypes = {
  className: PropTypes.string,
  rows: PropTypes.number,
};

export default Textarea;