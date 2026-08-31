import React from 'react';
import PropTypes from 'prop-types';

/**
 * Card component following the ToothWise design system.
 * Uses class names: tw-card, tw-card--flat, tw-hover-lift
 */
const Card = ({
  children,
  className = '',
  variant = 'default',
  hover = false,
  ...props
}) => {
  const variantClasses = {
    default: 'tw-card',
    flat: 'tw-card--flat',
  };

  const hoverClass = hover ? 'tw-hover-lift' : '';
  const combinedClassName = `tw-card ${variantClasses[variant] || variantClasses.default} ${hoverClass} ${className}`.trim();

  return (
    <div className={combinedClassName} {...props}>
      {children}
    </div>
  );
};

Card.propTypes = {
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  variant: PropTypes.oneOf(['default', 'flat']),
  hover: PropTypes.bool,
};

export default Card;
