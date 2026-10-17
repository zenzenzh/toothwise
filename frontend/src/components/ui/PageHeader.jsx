import React from 'react';
import PropTypes from 'prop-types';

/**
 * PageHeader — title, optional subtitle and right-aligned actions.
 * Reuses the .tw-page-header / .tw-page-title-wrap styles shared by all
 * staff pages so migrated and unmigrated pages look the same.
 */
const PageHeader = ({
  title,
  subtitle,
  actions,
  className = '',
}) => (
  <div className={`tw-page-header ${className}`.trim()}>
    <div className="tw-page-title-wrap">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
    {actions && <div className="tw-page-header__actions">{actions}</div>}
  </div>
);

PageHeader.propTypes = {
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.node,
  actions: PropTypes.node,
  className: PropTypes.string,
};

export default PageHeader;
