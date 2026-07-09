import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { sessionAPI } from "../../../api/academics";
import { FormCard, TextField, useFormSubmit } from "../../../components/forms";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Add/Edit Session (add/edit_session_template.html + SessionForm). */
export function SessionFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Session" : "Add Session";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { sessionId } = useParams();

  const [fields, setFields] = useState({ start_year: "", end_year: "" });

  useEffect(() => {
    if (!edit) return;
    sessionAPI
      .get(sessionId)
      .then((s) => setFields({ start_year: s.start_year, end_year: s.end_year }))
      .catch(() => addMessage("Could not load the session.", "danger"));
  }, [edit, sessionId, addMessage]);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () =>
      edit ? sessionAPI.update(sessionId, fields) : sessionAPI.create(fields),
    {
      onSuccess: () => {
        addMessage(
          edit ? "Session updated successfully!" : "Session created successfully!",
          "success"
        );
        navigate("/session/manage/");
      },
    }
  );

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Session" : "Add Session"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <TextField label="Start year" name="start_year" type="date" value={fields.start_year} onChange={setField} error={errors.start_year} required />
      <TextField label="End year" name="end_year" type="date" value={fields.end_year} onChange={setField} error={errors.end_year} required />
    </FormCard>
  );
}

/** Manage Sessions table (hod_template/manage_session.html). */
export function ManageSessions() {
  usePageHeader({
    title: "Manage Sessions",
    breadcrumb: [{ text: "Manage Sessions" }],
  });
  const { addMessage } = useMessages();
  const { data: sessions, reload } = useApi(() => sessionAPI.getAll());

  const remove = async (session) => {
    if (!window.confirm("Are you sure you want to delete this ?")) return;
    try {
      await sessionAPI.delete(session.id);
      addMessage("Session deleted successfully!", "success");
      reload();
    } catch {
      addMessage(
        "There are students assigned to this session. Please move them to another session.",
        "danger"
      );
    }
  };

  return (
    <ListCard title="Manage Sessions">
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Start</th>
            <th>End</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sessions?.map((session, i) => (
            <tr key={session.id}>
              <td>{i + 1}</td>
              <td>{session.start_year}</td>
              <td>{session.end_year}</td>
              <td>
                <Link to={`/session/edit/${session.id}`} className="btn btn-info">
                  Edit
                </Link>{" "}
                -{" "}
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={() => remove(session)}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}
