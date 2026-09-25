import React from 'react';
import PropTypes from 'prop-types';

/**
 * ConfirmDialog component following the ToothWise design system.
 * Used for destructive actions confirmation.
 */
const ConfirmDialog = ({
  open,
  onConfirm,
  onCancel,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'danger',
}) => {
  if (!open) return null;

  return (
    <div
      className="tw-modal-overlay"
      onClick={onCancel}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(2px)',
      }}
    >
      <div
        className="tw-modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--tw-white)',
          borderRadius: 'var(--tw-radius-lg)',
          padding: 'var(--tw-space-6)',
          width: '100%',
          maxWidth: '400px',
          boxShadow: 'var(--tw-shadow-xl)'
        }}
      >
        <h3 style={{ marginBottom: 'var(--tw-space-3)', color: 'var(--tw-burgundy)' }}>{title}</h3>
        <p style={{ fontSize: 'var(--tw-text-caption)', color: 'var(--tw-muted)' }}>{message}</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--tw-space-3)', marginTop: 'var(--tw-space-6)' }}>
          <button className="tw-btn tw-btn--secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button
            className={`tw-btn ${variant === 'danger' ? 'tw-btn--danger' : 'tw-btn--primary'}`}
            onClick={onConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

ConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  variant: PropTypes.oneOf(['danger', 'primary']),
};

export default ConfirmDialog;