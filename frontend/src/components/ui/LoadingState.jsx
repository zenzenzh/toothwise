import React from 'react';
import PropTypes from 'prop-types';

/**
 * LoadingState component following the ToothWise design system.
 * Uses the 'skeleton' class for shimmer effect.
 */
const LoadingState = ({
  type = 'default',
  count = 1,
  className = '',
}) => {
  if (type === 'page') {
    return (
      <div className={`tw-page ${className}`}>
        <div className="skeleton" style={{ height: 40, width: '40%', marginBottom: 'var(--tw-space-4)' }} />
        <div className="skeleton" style={{ height: 20, width: '60%', marginBottom: 'var(--tw-space-6)' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 'var(--tw-space-4)' }}>
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 120, borderRadius: 'var(--tw-radius-lg)' }} />
          ))}
        </div>
      </div>
    );
  }

  if (type === 'list') {
    return (
      <div className={className}>
        {[...Array(count)].map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 48, marginBottom: 'var(--tw-space-2)', borderRadius: 'var(--tw-radius-sm)' }} />
        ))}
      </div>
    );
  }

  if (type === 'table') {
    return (
      <div className="tw-table-card">
        <table className="tw-table">
          <tbody>
            {[...Array(count)].map((_, i) => (
              <tr key={i}>
                <td colSpan={100} style={{ padding: 'var(--tw-space-4)' }}>
                  <div className="skeleton" style={{ height: 24 }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Default type
  return (
    <div className={`tw-state ${className}`}>
      <div className="skeleton" style={{ width: 100, height: 100, borderRadius: '50%' }} />
      <p className="skeleton" style={{ height: 20, width: '60%' }} />
    </div>
  );
};

LoadingState.propTypes = {
  type: PropTypes.oneOf(['default', 'page', 'list', 'table']),
  count: PropTypes.number,
  className: PropTypes.string,
};

export default LoadingState;
