import React from 'react';
import PropTypes from 'prop-types';

/**
 * Input component following the ToothWise design system.
 */
const Input = ({
  type = 'text',
  className = '',
  ...props
}) => {
  return (
    <input
      type={type}
      className={`tw-input ${className}`}
      {...props}
    />
  );
};

Input.propTypes = {
  type: PropTypes.string,
  className: PropTypes.string,
};

export default Input;