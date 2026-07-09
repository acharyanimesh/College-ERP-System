import { useState } from "react";
import leaveAPI from "../../api/leave";
import { FormCard, TextAreaField, TextField, useFormSubmit } from "../../components/forms";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const STATUS_BADGES = {
  0: ["badge-warning", "Pending"],
  1: ["badge-success", "Accepted"],
  "-1": ["badge-danger", "Rejected"],
};

/**
 * Apply for Leave + history, shared by staff and students
 * (staff_apply_leave.html / student_apply_leave.html — identical layout).
 */
function ApplyLeave({ role }) {
  usePageHeader({
    title: "Apply for Leave",
    breadcrumb: [{ text: "Apply for Leave" }],
  });
  const { addMessage } = useMessages();
  const [fields, setFields] = useState({ date: "", message: "" });
  const { data: history, reload } = useApi(() => leaveAPI.getMine(role), [role]);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => leaveAPI.apply(role, fields),
    {
      onSuccess: () => {
        addMessage("Application for leave has been submitted for review", "success");
        setFields({ date: "", message: "" });
        reload();
      },
    }
  );

  return (
    <>
      <FormCard
        title="Apply for Leave"
        onSubmit={handleSubmit}
        buttonText="Apply For Leave"
        nonFieldError={nonFieldError}
        submitting={submitting}
      >
        <TextField label="Date" name="date" type="date" value={fields.date} onChange={setField} error={errors.date} required />
        <TextAreaField label="Message" name="message" value={fields.message} onChange={setField} error={errors.message} required />
      </FormCard>

      <div className="card card-default">
        <div className="card-header">
          <h3 className="card-title">
            <b>Leave History</b>
          </h3>
        </div>
        <div className="table p-2" style={{ overflowX: "auto", overflowY: "auto", maxHeight: 500 }}>
          <table className="table table-bordered table-hover" style={{ minWidth: 600 }}>
            <thead className="thead-dark">
              <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Message</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history?.map((leave, i) => {
                const [cls, text] = STATUS_BADGES[String(leave.status)] || [];
                return (
                  <tr key={leave.id}>
                    <td>{i + 1}</td>
                    <td>{leave.date}</td>
                    <td
                      style={{
                        wordWrap: "break-word",
                        maxWidth: 200,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {leave.message}
                    </td>
                    <td>
                      <span className={`badge ${cls}`}>{text}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default ApplyLeave;
