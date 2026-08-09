import { useState } from "react";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const EMPTY = {
  name: "",
  code: "",
  description: "",
  recurring: true,
  refundable: false,
};

/**
 * The college's chart of fees — Tuition, Admission, Exam, Lab.
 *
 * A master list rather than free text on each structure, so "how much
 * tuition did we collect?" stays a question the reports can answer.
 */
function FeeHeads() {
  usePageHeader({ title: "Fee Heads", breadcrumb: [{ text: "Fee Heads" }] });
  const { addMessage } = useMessages();
  const { data: heads, reload } = useApi(() => feeAPI.getHeads());

  const [editing, setEditing] = useState(null); // head id, or null for "new"
  const [fields, setFields] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const startNew = () => {
    setEditing(null);
    setFields(EMPTY);
    setErrors({});
  };

  const startEdit = (head) => {
    setEditing(head.id);
    setFields({ ...EMPTY, ...head });
    setErrors({});
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      if (editing) await feeAPI.updateHead(editing, fields);
      else await feeAPI.createHead(fields);
      addMessage(editing ? "Fee head updated." : "Fee head added.", "success");
      startNew();
      reload();
    } catch (err) {
      const data = err.response?.data || {};
      setErrors(data);
      if (data.detail) addMessage(data.detail, "danger");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (head) => {
    if (!window.confirm(`Delete the "${head.name}" fee head?`)) return;
    try {
      await feeAPI.deleteHead(head.id);
      addMessage("Fee head deleted.", "success");
      if (editing === head.id) startNew();
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not delete the fee head.",
        "danger"
      );
    }
  };

  return (
    <>
      <ListCard
        title={editing ? "Edit Fee Head" : "Add Fee Head"}
        action={
          editing && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={startNew}
            >
              Cancel edit
            </button>
          )
        }
      >
        <form onSubmit={save}>
          <div className="row">
            <div className="col-md-4 form-group">
              <label>Name</label>
              <input
                className={`form-control ${errors.name ? "is-invalid" : ""}`}
                value={fields.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="Tuition"
                required
              />
              {errors.name && (
                <div className="invalid-feedback d-block">{errors.name[0]}</div>
              )}
            </div>
            <div className="col-md-2 form-group">
              <label>Code</label>
              <input
                className="form-control"
                value={fields.code}
                onChange={(e) => setField("code", e.target.value)}
                placeholder="TUI"
              />
            </div>
            <div className="col-md-6 form-group">
              <label>Description</label>
              <input
                className="form-control"
                value={fields.description}
                onChange={(e) => setField("description", e.target.value)}
              />
            </div>
          </div>
          <div className="row">
            <div className="col-md-3 form-group">
              <div className="form-check">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="recurring"
                  checked={!!fields.recurring}
                  onChange={(e) => setField("recurring", e.target.checked)}
                />
                <label className="form-check-label" htmlFor="recurring">
                  Charged every semester
                </label>
              </div>
            </div>
            <div className="col-md-4 form-group">
              <div className="form-check">
                <input
                  type="checkbox"
                  className="form-check-input"
                  id="refundable"
                  checked={!!fields.refundable}
                  onChange={(e) => setField("refundable", e.target.checked)}
                />
                <label className="form-check-label" htmlFor="refundable">
                  Refundable deposit
                </label>
              </div>
              <small className="text-muted">
                Money the college is holding, not money it has earned — reports
                keep the two apart.
              </small>
            </div>
          </div>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : editing ? "Update Fee Head" : "Add Fee Head"}
          </button>
        </form>
      </ListCard>

      <ListCard title="Fee Heads" scrollBody>
        <table className="table table-bordered table-hover">
          <thead className="thead-dark">
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>Code</th>
              <th>Description</th>
              <th>Type</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {!heads?.length && (
              <tr>
                <td colSpan={6} className="text-center">
                  No fee heads yet. Add Tuition, Exam and the rest above, then
                  build a fee structure from them.
                </td>
              </tr>
            )}
            {heads?.map((head, i) => (
              <tr key={head.id}>
                <td>{i + 1}</td>
                <td>{head.name}</td>
                <td>{head.code || "—"}</td>
                <td>{head.description || "—"}</td>
                <td>
                  {head.recurring ? (
                    <span className="badge badge-info">Every semester</span>
                  ) : (
                    <span className="badge badge-secondary">One-off</span>
                  )}{" "}
                  {head.refundable && (
                    <span className="badge badge-warning">Refundable</span>
                  )}
                </td>
                <td className="text-nowrap">
                  <button
                    type="button"
                    className="btn btn-sm btn-info"
                    title="Edit"
                    onClick={() => startEdit(head)}
                  >
                    <i className="fas fa-edit"></i>
                  </button>{" "}
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    title="Delete"
                    onClick={() => remove(head)}
                  >
                    <i className="fas fa-trash"></i>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ListCard>
    </>
  );
}

export default FeeHeads;
