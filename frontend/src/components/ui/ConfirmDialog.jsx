import React, { useRef } from 'react';
import PropTypes from 'prop-types';
import { TriangleAlert } from 'lucide-react';
import Modal from './Modal';

/**
 * ConfirmDialog — branded replacement for window.confirm.
 * Focus starts on Cancel so Enter never triggers a destructive action by
 * accident. While `busy`, both buttons are disabled and Esc is ignored.
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
  busy = false,
}) => {
  const cancelRef = useRef(null);

  return (
    <Modal
      isOpen={open}
      onClose={onCancel}
      title={title}
      icon={variant === 'danger' ? TriangleAlert : undefined}
      className={`tw6-modal--confirm tw6-modal--${variant}`}
      initialFocus={cancelRef}
      dismissible={!busy}
    >
      <div className="tw6-modal-form">
        <div className="tw6-confirm-message">{message}</div>
        <div className="tw6-modal-footer">
          <button ref={cancelRef} type="button" className="tw6-modal-cancel" onClick={onCancel} disabled={busy}>
            {cancelText}
          </button>
          <button
            type="button"
            className={`tw6-modal-save ${variant === 'danger' ? 'tw6-modal-save--danger' : ''}`.trim()}
            onClick={onConfirm}
            disabled={busy}
            aria-busy={busy}
          >
            {busy ? 'Working…' : confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
};

ConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.node.isRequired,
  confirmText: PropTypes.string,
  cancelText: PropTypes.string,
  variant: PropTypes.oneOf(['danger', 'primary']),
  busy: PropTypes.bool,
};

export default ConfirmDialog;
