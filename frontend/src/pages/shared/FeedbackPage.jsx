import { useState } from "react";
import feedbackAPI from "../../api/feedback";
import { FormCard, TextAreaField, useFormSubmit } from "../../components/forms";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Add Feedback + history, shared by staff and students
 * (staff_feedback.html / student_feedback.html — identical layout).
 */
function FeedbackPage({ role }) {
  usePageHeader({
    title: "Add Feedback",
    breadcrumb: [{ text: "Add Feedback" }],
  });
  const { addMessage } = useMessages();
  const [feedback, setFeedback] = useState("");
  const { data: feedbacks, reload } = useApi(() => feedbackAPI.getMine(role), [role]);

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => feedbackAPI.submit(role, feedback),
    {
      onSuccess: () => {
        addMessage("Feedback submitted for review", "success");
        setFeedback("");
        reload();
      },
    }
  );

  return (
    <>
      <FormCard
        title="Add Feedback"
        onSubmit={handleSubmit}
        buttonText="Submit Feedback"
        nonFieldError={nonFieldError}
        submitting={submitting}
      >
        <TextAreaField
          label="Feedback"
          name="feedback"
          value={feedback}
          onChange={(_, v) => setFeedback(v)}
          error={errors.feedback}
          required
        />
      </FormCard>

      <div className="card card-dark">
        <div className="card-header">
          <h3 className="card-title">Add Feedback</h3>
        </div>
        <div className="table p-2" style={{ overflowX: "auto", overflowY: "auto", maxHeight: 500 }}>
          <table className="table table-bordered" style={{ minWidth: 700 }}>
            <tbody>
              <tr>
                <th>ID</th>
                <th>Feedback</th>
                <th>Reply</th>
                <th>Created At</th>
              </tr>
              {feedbacks?.map((f, i) => (
                <tr key={f.id}>
                  <td>{i + 1}</td>
                  <td
                    style={{
                      wordWrap: "break-word",
                      maxWidth: 250,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {f.feedback}
                  </td>
                  <td
                    style={{
                      wordWrap: "break-word",
                      maxWidth: 200,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {f.reply ? (
                      f.reply
                    ) : (
                      <p className="badge badge-warning">No Response Yet</p>
                    )}
                  </td>
                  <td>{f.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default FeedbackPage;
