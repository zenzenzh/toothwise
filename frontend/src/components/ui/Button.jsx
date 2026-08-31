import React from 'react';
import PropTypes from 'prop-types';

/**
 * Button component following the ToothWise design system.
 * Uses class names: tw-btn, tw-btn--primary, tw-btn--rose, tw-btn--secondary, tw-btn--ghost, tw-btn--danger, tw-btn--sm, tw-btn--lg
 */
const Button = ({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  icon: Icon,
  iconPosition = 'left',
  ...props
}) => {
  // Map variants to class names
  const variantClasses = {
    primary: 'tw-btn--primary',
    rose: 'tw-btn--rose',
    secondary: 'tw-btn--secondary',
    ghost: 'tw-btn--ghost',
    danger: 'tw-btn--danger',
  };

  // Map sizes to class names
  const sizeClasses = {
    sm: 'tw-btn--sm',
    md: '', // default
    lg: 'tw-btn--lg',
  };

  const combinedClassName = `tw-btn ${variantClasses[variant] || variantClasses.primary} ${sizeClasses[size] || ''} ${className}`.trim();

  const content = (
    <>
      {Icon && iconPosition === 'left' && <Icon size={18} />}
      {children}
      {Icon && iconPosition === 'right' && <Icon size={18} />}
    </>
  );

  return (
    <button
      type={type}
      className={combinedClassName}
      onClick={onClick}
      disabled={disabled}
      {...props}
    >
      {content}
    </button>
  );
};

Button.propTypes = {
  children: PropTypes.node.isRequired,
  onClick: PropTypes.func,
  type: PropTypes.oneOf(['button', 'submit', 'reset']),
  variant: PropTypes.oneOf(['primary', 'rose', 'secondary', 'ghost', 'danger']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  className: PropTypes.string,
  disabled: PropTypes.bool,
  icon: PropTypes.elementType,
  iconPosition: PropTypes.oneOf(['left', 'right']),
};

export default Button;
