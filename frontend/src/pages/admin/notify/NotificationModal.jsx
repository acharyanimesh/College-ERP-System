import { useEffect, useState } from "react";
import Modal from "../../../components/Modal";

/**
 * Send-notification modal shared by the notify pages
 * (_notify_student_modal.html / the inline modal in staff_notification.html).
 * `onSend(message)` does the API call; resolves on success.
 */
function NotificationModal({ show, onClose, onSend }) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (show) setMessage("");
  }, [show]);

  const send = async () => {
    if (message.trim() === "") {
      window.alert("Please enter a message before sending.");
      return;
    }
    setSending(true);
    try {
      await onSend(message);
      window.alert("Notification Sent");
      onClose();
    } catch {
      window.alert("Notification could not be saved. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal
      show={show}
      onClose={onClose}
      header="Send Notification"
      footer={
        <button
          type="button"
          className="btn btn-success"
          onClick={send}
          disabled={sending}
        >
          Send Notification
        </button>
      }
    >
      <div className="form-group">
        <label htmlFor="message">Message</label>
        <textarea
          id="message"
          rows={4}
          className="form-control"
          placeholder="Type your message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        ></textarea>
      </div>
    </Modal>
  );
}

export default NotificationModal;
