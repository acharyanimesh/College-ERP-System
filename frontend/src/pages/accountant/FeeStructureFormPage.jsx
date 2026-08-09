import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { courseAPI, sessionAPI } from "../../api/academics";
import feeAPI from "../../api/fees";
import { BackButton, ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const EMPTY_ROW = { head: "", amount: "" };

/**
 * Write what a (course, session, semester) costs.
 *
 * The rows are sent as a whole and REPLACE whatever the structure had — a
 * structure is a short list somebody edits all at once, and "these are the
 * heads now" can't get half-applied the way a diff can.
 *
 * Editing this never touches a bill already issued: FeeInvoiceLine copies the
 * amounts at issue time, so a correction here changes what the NEXT run
 * charges and nothing else.
 */
function FeeStructureFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Fee Structure" : "New Fee Structure";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { structureId } = useParams();

  const { data: courses } = useApi(() => courseAPI.getAll());
  const { data: sessions } = useApi(() => sessionAPI.getAll());
  const { data: heads } = useApi(() => feeAPI.getHeads());

  const [fields, setFields] = useState({
    course: "",
    session: "",
    semester: 1,
    due_days: 30,
    late_fine_per_day: "0",
    note: "",
  });
  const [rows, setRows] = useState([{ ...EMPTY_ROW }]);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!edit) return;
    feeAPI
      .getStructure(structureId)
      .then((s) => {
        setFields({
          course: s.course,
          session: s.session,
          semester: s.semester,
          due_days: s.due_days,
          late_fine_per_day: String(s.late_fine_per_day ?? "0"),
          note: s.note || "",
        });
        setRows(
          s.items?.length
            ? s.items.map((i) => ({ head: i.head, amount: String(i.amount) }))
            : [{ ...EMPTY_ROW }]
        );
      })
      .catch(() => addMessage("Could not load the fee structure.", "danger"));
  }, [edit, structureId, addMessage]);

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const setRow = (index, name, value) =>
    setRows((rs) => rs.map((r, i) => (i === index ? { ...r, [name]: value } : r)));

  const addRow = () => setRows((rs) => [...rs, { ...EMPTY_ROW }]);
  const removeRow = (index) =>
    setRows((rs) => (rs.length === 1 ? rs : rs.filter((_, i) => i !== index)));

  // Display only. The server recomputes this from the rows it is sent — a
  // total worked out here is one that can disagree with the bill.
  const previewTotal = rows.reduce((sum, r) => sum + (Number(r.amount) || 0), 0);

  // Heads already chosen can't be picked twice on one structure.
  const takenHeads = new Set(rows.map((r) => String(r.head)).filter(Boolean));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    const payload = {
      ...fields,
      items: rows
        .filter((r) => r.head !== "")
        .map((r) => ({ head: r.head, amount: r.amount })),
    };
    try {
      if (edit) await feeAPI.updateStructure(structureId, payload);
      else await feeAPI.createStructure(payload);
      addMessage(edit ? "Fee structure updated." : "Fee structure created.", "success");
      navigate("/accountant/fees/structures/");
    } catch (err) {
      const data = err.response?.data || {};
      setErrors(data);
      if (data.detail) addMessage(data.detail, "danger");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ListCard
      title={pageTitle}
      action={<BackButton to="/accountant/fees/structures/">Back to Fee Structures</BackButton>}
    >
      <form onSubmit={save}>
        <div className="row">
          <div className="col-md-4 form-group">
            <label>Course</label>
            <select
              className="form-control"
              value={fields.course}
              onChange={(e) => setField("course", e.target.value)}
              required
            >
              <option value="">Select a course</option>
              {courses?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_with_abbr}
                </option>
              ))}
            </select>
            {errors.course && (
              <div className="text-danger small">{errors.course[0]}</div>
            )}
          </div>
          <div className="col-md-4 form-group">
            <label>Session</label>
            <select
              className="form-control"
              value={fields.session}
              onChange={(e) => setField("session", e.target.value)}
              required
            >
              <option value="">Select a session</option>
              {sessions?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
            {errors.session && (
              <div className="text-danger small">{errors.session[0]}</div>
            )}
          </div>
          <div className="col-md-4 form-group">
            <label>Semester</label>
            <input
              type="number"
              min={1}
              className="form-control"
              value={fields.semester}
              onChange={(e) => setField("semester", e.target.value)}
              required
            />
          </div>
        </div>

        <div className="row">
          <div className="col-md-4 form-group">
            <label>Due this many days after issue</label>
            <input
              type="number"
              min={0}
              className="form-control"
              value={fields.due_days}
              onChange={(e) => setField("due_days", e.target.value)}
            />
          </div>
          <div className="col-md-4 form-group">
            <label>Late fine per day (Rs.)</label>
            <input
              type="number"
              min={0}
              step="0.01"
              className="form-control"
              value={fields.late_fine_per_day}
              onChange={(e) => setField("late_fine_per_day", e.target.value)}
            />
            <small className="text-muted">
              Zero if this college doesn&apos;t fine late fees.
            </small>
          </div>
          <div className="col-md-4 form-group">
            <label>Note</label>
            <input
              className="form-control"
              value={fields.note}
              onChange={(e) => setField("note", e.target.value)}
            />
          </div>
        </div>

        <h5 className="mt-3">Fee Heads</h5>
        {errors.items && (
          <div className="alert alert-danger">
            {[].concat(errors.items).map((message, i) => (
              <div key={i}>{message}</div>
            ))}
          </div>
        )}
        <table className="table table-bordered">
          <thead className="thead-dark">
            <tr>
              <th style={{ width: "50%" }}>Head</th>
              <th>Amount (Rs.)</th>
              <th style={{ width: 60 }}></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                <td>
                  <select
                    className="form-control"
                    value={row.head}
                    onChange={(e) => setRow(index, "head", e.target.value)}
                  >
                    <option value="">Select a fee head</option>
                    {heads?.map((h) => (
                      <option
                        key={h.id}
                        value={h.id}
                        disabled={
                          takenHeads.has(String(h.id)) &&
                          String(row.head) !== String(h.id)
                        }
                      >
                        {h.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    className="form-control"
                    value={row.amount}
                    onChange={(e) => setRow(index, "amount", e.target.value)}
                    placeholder="0.00"
                  />
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-sm btn-danger"
                    onClick={() => removeRow(index)}
                    disabled={rows.length === 1}
                    title="Remove this row"
                  >
                    <i className="fas fa-times"></i>
                  </button>
                </td>
              </tr>
            ))}
            <tr>
              <td className="text-right font-weight-bold">Total</td>
              <td className="font-weight-bold">{formatMoney(previewTotal)}</td>
              <td></td>
            </tr>
          </tbody>
        </table>

        {!heads?.length && (
          <div className="alert alert-warning">
            There are no fee heads yet — add Tuition, Exam and the rest on the
            Fee Heads page first.
          </div>
        )}

        <button type="button" className="btn btn-secondary btn-sm" onClick={addRow}>
          <i className="fas fa-plus me-1"></i> Add a head
        </button>
        <hr />
        <button className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : edit ? "Update Structure" : "Create Structure"}
        </button>
        {edit && (
          <small className="d-block text-muted mt-2">
            Bills already issued from this structure keep the amounts they were
            raised with — editing here only changes what the next invoice run
            charges.
          </small>
        )}
      </form>
    </ListCard>
  );
}

export default FeeStructureFormPage;
