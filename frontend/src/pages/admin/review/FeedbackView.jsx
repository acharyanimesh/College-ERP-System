import { useState } from "react";
import feedbackAPI from "../../../api/feedback";
import { ListCard } from "../../../components/ListCard";
import Modal from "../../../components/Modal";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/**
 * Admin feedback review for staff or students
 * (staff_feedback_template.html / student_feedback_template.html):
 * unreplied rows get a Reply button opening the reply modal.
 */
function FeedbackView({ role }) {
  const isStaff = role === "staff";
  const pageTitle = isStaff
    ? "Staff Feedback Messages"
    : "Student Feedback Messages";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });

  const { data: feedbacks, reload } = useApi(() => feedbackAPI.getAll(role), [role]);
  const [target, setTarget] = useState(null); // { id, name }
  const [reply, setReply] = useState("");

  const submit = async () => {
    if (reply.trim() === "") {
      window.alert("Please enter a reply message.");
      return;
    }
    try {
      await feedbackAPI.reply(role, target.id, reply);
      window.alert("Reply Sent");
      setTarget(null);
      setReply("");
      reload();
    } catch {
      window.alert("Reply Could Not Be Sent");
    }
  };

  return (
    <ListCard dark title={pageTitle}>
      <table className="table table-bordered table-hover">
        <tbody>
          <tr>
            <th>#</th>
            <th>{isStaff ? "Staff" : "Student"}</th>
            <th>Course</th>
            <th>Message</th>
            <th>Sent On</th>
            <th>Replied On</th>
            <th>Action</th>
          </tr>
          {feedbacks?.map((feedback, i) => (
            <tr key={feedback.id}>
              <td>{i + 1}</td>
              <td>{feedback.person_name}</td>
              <td>
                {feedback.course_names || <span className="text-muted">—</span>}
              </td>
              <td>{feedback.feedback}</td>
              <td>{feedback.created_at}</td>
              {!feedback.reply ? (
                <>
                  <td>
                    <span className="badge badge-warning">Pending Response</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-success"
                      onClick={() => {
                        setTarget({ id: feedback.id, name: feedback.person_name });
                        setReply("");
                      }}
                    >
                      Reply
                    </button>
                  </td>
                </>
              ) : (
                <>
                  <td>{feedback.updated_at}</td>
                  <td>{feedback.reply}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <Modal
        show={target !== null}
        onClose={() => setTarget(null)}
        header=""
        footer={
          <button type="button" className="btn btn-success" onClick={submit}>
            Reply
          </button>
        }
      >
        <p>
          Reply <span>{target?.name}</span>
        </p>
        <textarea
          cols={30}
          rows={10}
          className="form-control"
          value={reply}
          onChange={(e) => setReply(e.target.value)}
        ></textarea>
      </Modal>
    </ListCard>
  );
}

export default FeedbackView;
