import React, { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';
import { X } from 'lucide-react';

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal — the shared dialog shell (tw6-modal styles).
 * Renders into document.body, locks page scroll, closes on Esc / backdrop,
 * keeps Tab focus inside, and returns focus to the opener on close.
 * `initialFocus` (a ref) picks the element focused on open; otherwise the
 * first form field, then the first button.
 */
const Modal = ({
  isOpen,
  onClose,
  title,
  icon: Icon,
  children,
  className = '',
  initialFocus,
  dismissible = true,
}) => {
  const titleId = useId();
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const dismissibleRef = useRef(dismissible);
  onCloseRef.current = onClose;
  dismissibleRef.current = dismissible;

  useEffect(() => {
    if (!isOpen) return undefined;
    const opener = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const dialog = dialogRef.current;
    const target = initialFocus?.current
      || dialog?.querySelector('input:not([disabled]), select, textarea')
      || dialog?.querySelector(FOCUSABLE);
    target?.focus();

    const onKeyDown = (e) => {
      if (e.key === 'Escape' && dismissibleRef.current) {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab' || !dialog) return;
      const items = [...dialog.querySelectorAll(FOCUSABLE)];
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (opener && typeof opener.focus === 'function') opener.focus();
    };
  }, [isOpen, initialFocus]);

  if (!isOpen) return null;

  return createPortal(
    <div className="tw6-modal-overlay" onMouseDown={(e) => { if (dismissible && e.target === e.currentTarget) onClose(); }}>
      <div
        ref={dialogRef}
        className={`tw6-modal ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="tw6-modal-head">
          <div className="tw6-modal-heading">
            {Icon && <span className="tw6-modal-icon" aria-hidden="true"><Icon size={19} /></span>}
            <h3 id={titleId}>{title}</h3>
          </div>
          {dismissible && (
            <button type="button" className="tw6-modal-close" onClick={onClose} aria-label="Close dialog">
              <X size={18} aria-hidden="true" />
            </button>
          )}
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
};

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.node.isRequired,
  icon: PropTypes.elementType,
  children: PropTypes.node.isRequired,
  className: PropTypes.string,
  initialFocus: PropTypes.shape({ current: PropTypes.any }),
  dismissible: PropTypes.bool,
};

export default Modal;
