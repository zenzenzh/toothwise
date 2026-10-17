import React from 'react';
import PropTypes from 'prop-types';

/**
 * FormField — label + control + inline error for tw6-modal forms, wired
 * together for screen readers. `children` is a render function that
 * receives the props to spread onto the control:
 *
 *   <FormField id="x" label="Name" required error={err}>
 *     {a => <input {...a} className="tw6-modal-input" … />}
 *   </FormField>
 */
const FormField = ({ id, label, required = false, error, hint, className = '', children }) => {
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined;
  return (
    <div className={`tw6-modal-field ${className}`.trim()}>
      <label className="tw6-modal-label" htmlFor={id}>
        {label}{required && <span aria-hidden="true"> *</span>}
      </label>
      {children({ id, 'aria-invalid': !!error, 'aria-describedby': describedBy, required })}
      {hint && !error && <p id={hintId} className="tw6-modal-hint">{hint}</p>}
      {error && <p id={errorId} className="tw6-modal-error" role="alert">{error}</p>}
    </div>
  );
};

FormField.propTypes = {
  id: PropTypes.string.isRequired,
  label: PropTypes.node.isRequired,
  required: PropTypes.bool,
  error: PropTypes.string,
  hint: PropTypes.node,
  className: PropTypes.string,
  children: PropTypes.func.isRequired,
};

export default FormField;
