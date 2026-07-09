/**
 * Controlled Bootstrap modal (replaces the data-bs-toggle modals + the
 * $('#myModal').appendTo('body') trick in the templates).
 */
function Modal({ show, onClose, header, footer, children }) {
  if (!show) return null;
  return (
    <>
      <div
        className="modal fade show d-block"
        tabIndex={-1}
        role="dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              {header}
              <button
                type="button"
                className="btn-close"
                aria-hidden="true"
                onClick={onClose}
              ></button>
            </div>
            <div className="modal-body">{children}</div>
            <div className="modal-footer">
              <button type="button" className="btn btn-danger" onClick={onClose}>
                Close
              </button>
              {footer}
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </>
  );
}

export default Modal;
