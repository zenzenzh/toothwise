import React from 'react';
import PropTypes from 'prop-types';

/**
 * Modal component following the ToothWise design system.
 * Handles backdrop and containment.
 */
const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  className = '',
  footer,
  ...props
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="tw-modal-overlay"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(58, 36, 48, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(2px)',
      }}
    >
      <div
        className={`tw-modal ${className}`}
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--tw-white)',
          borderRadius: 'var(--tw-radius-xl)',
          padding: 'var(--tw-space-6)',
          width: '100%',
          maxWidth: '520px',
          boxShadow: 'var(--tw-shadow-xl)',
        }}
        {...props}
      >
        {title && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--tw-space-6)'
          }}>
            <h3 style={{
              margin: 0,
              fontSize: 'var(--tw-text-h2)',
              color: 'var(--tw-burgundy)'
            }}>{title}</h3>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                fontSize: '20px',
                color: 'var(--tw-muted)',
                cursor: 'pointer'
              }}
              aria-label="Close modal"
            >
              ✕
            </button>
          </div>
        )}

        {children}

        {footer && (
          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 'var(--tw-space-3)',
            marginTop: 'var(--tw-space-6)'
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string,
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  footer: PropTypes.node,
};

export default Modal;
