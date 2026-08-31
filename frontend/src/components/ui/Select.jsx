import React from 'react';
import PropTypes from 'prop-types';

/**
 * Select component following the ToothWise design system.
 */
const Select = ({
  className = '',
  placeholder,
  ...props
}) => {
  return (
    <select className={`tw-select ${className}`} {...props}>
      {placeholder && <option value="" disabled>{placeholder}</option>}
    </select>
  );
};

Select.propTypes = {
  className: PropTypes.string,
  placeholder: PropTypes.string,
};

export default Select;