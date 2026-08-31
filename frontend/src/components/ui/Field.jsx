import React from 'react';
import PropTypes from 'prop-types';

/**
 * Input and Form field component following the ToothWise design system.
 * Handles labels, error messages, and consistent styling.
 */
const Field = ({
  label,
  error,
  children,
  className = '',
  helperText,
  ...props
}) => {
  const containerClasses = `tw-field ${error ? 'tw-field--error' : ''} ${className}`.trim();

  return (
    <div className={containerClasses} {...props}>
      {label && <label className="tw-label">{label}</label>}
      {children}
      {error && <p className="tw-field-error" role="alert">{error}</p>}
      {helperText && !error && <p className="tw-meta" style={{ marginTop: 'var(--tw-space-1)' }}>{helperText}</p>}
    </div>
  );
};

Field.propTypes = {
  label: PropTypes.string,
  error: PropTypes.string,
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  helperText: PropTypes.string,
};

export default Field;
