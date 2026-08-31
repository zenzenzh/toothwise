import React from 'react';
import PropTypes from 'prop-types';

/**
 * PageHeader component following the ToothWise design system.
 * Consistent header across all pages.
 */
const PageHeader = ({
  title,
  subtitle,
  actions,
  className = '',
}) => {
  return (
    <div className={`tw-page-header ${className}`}>
      <div>
        <h1 className="tw-page-header__title">{title}</h1>
        {subtitle && <p className="tw-page-header__subtitle">{subtitle}</p>}
      </div>
      {actions && <div style={{ display: 'flex', gap: 'var(--tw-space-3)' }}>{actions}</div>}
    </div>
  );
};

PageHeader.propTypes = {
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string,
  actions: PropTypes.node,
  className: PropTypes.string,
};

export default PageHeader;