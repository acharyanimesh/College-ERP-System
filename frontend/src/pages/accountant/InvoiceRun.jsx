import { useState } from "react";
import { Link } from "react-router-dom";
import { courseAPI, sessionAPI } from "../../api/academics";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Raise a semester's bills for a class.
 *
 * Preview first, deliberately: an invoice run is the one action here that
 * reaches every student at once, and the accountant should see who it will
 * touch before it touches them. Running it twice is safe either way — the
 * database refuses a second bill for the same student and semester, so a
 * re-run only picks up whoever joined since.
 */
function InvoiceRun() {
  usePageHeader({
    title: "Raise Fee Invoices",
    breadcrumb: [{ text: "Raise Fee Invoices" }],
  });
  const { addMessage } = useMessages();

  const { data: courses } = useApi(() => courseAPI.getAll());
  const { data: sessions } = useApi(() => sessionAPI.getAll());

  const [target, setTarget] = useState({ course: "", session: "", semester: 1 });
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const ready = target.course && target.session && target.semester;

  const setField = (name, value) => {
    setTarget((t) => ({ ...t, [name]: value }));
    setPreview(null);
    setResult(null);
  };

  const loadPreview = async () => {
    setLoading(true);
    setResult(null);
    try {
      setPreview(await feeAPI.previewRun(target));
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not work out who would be billed.",
        "danger"
      );
    } finally {
      setLoading(false);
    }
  };

  const run = async () => {
    setRunning(true);
    try {
      const outcome = await feeAPI.run(target);
      setResult(outcome);
      addMessage(outcome.detail, "success");
      setPreview(await feeAPI.previewRun(target));
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not raise the invoices.",
        "danger"
      );
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <ListCard title="Pick a class">
        <div className="row">
          <div className="col-md-4 form-group">
            <label>Course</label>
            <select
              className="form-control"
              value={target.course}
              onChange={(e) => setField("course", e.target.value)}
            >
              <option value="">Select a course</option>
              {courses?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_with_abbr}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4 form-group">
            <label>Session</label>
            <select
              className="form-control"
              value={target.session}
              onChange={(e) => setField("session", e.target.value)}
            >
              <option value="">Select a session</option>
              {sessions?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4 form-group">
            <label>Semester</label>
            <input
              type="number"
              min={1}
              className="form-control"
              value={target.semester}
              onChange={(e) => setField("semester", e.target.value)}
            />
          </div>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={loadPreview}
          disabled={!ready || loading}
        >
          {loading ? "Checking…" : "See who would be billed"}
        </button>
      </ListCard>

      {preview && (
        <ListCard
          title={`${preview.course_name} · Semester ${preview.semester} · ${preview.session_name}`}
        >
          {!preview.structure ? (
            <div className="alert alert-warning mb-0">
              <strong>No fee structure for this class.</strong> Nothing can be
              billed until one exists —{" "}
              <Link to="/accountant/fees/structures/add">write one</Link> and
              come back.
            </div>
          ) : (
            <>
              <p>
                Each student will be billed{" "}
                <strong>{formatMoney(preview.structure.total)}</strong>, due{" "}
                {preview.structure.due_days} days after issue:{" "}
                {preview.structure.items.map((item) => (
                  <span key={item.id} className="badge badge-info mr-1">
                    {item.head_name} {formatMoney(item.amount)}
                  </span>
                ))}
              </p>

              <div className="row">
                <div className="col-md-6">
                  <h5>
                    To be billed{" "}
                    <span className="badge badge-primary">
                      {preview.to_bill.length}
                    </span>
                  </h5>
                  <table className="table table-bordered table-sm">
                    <thead className="thead-dark">
                      <tr>
                        <th>Roll</th>
                        <th>Student</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.to_bill.length ? (
                        preview.to_bill.map((s) => (
                          <tr key={s.id}>
                            <td>{s.roll_number || "—"}</td>
                            <td>{s.name}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={2} className="text-center">
                            Nobody left to bill in this class.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="col-md-6">
                  <h5>
                    Already billed{" "}
                    <span className="badge badge-secondary">
                      {preview.already_billed.length}
                    </span>
                  </h5>
                  <table className="table table-bordered table-sm">
                    <thead className="thead-dark">
                      <tr>
                        <th>Roll</th>
                        <th>Student</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.already_billed.length ? (
                        preview.already_billed.map((s) => (
                          <tr key={s.id}>
                            <td>{s.roll_number || "—"}</td>
                            <td>{s.name}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={2} className="text-center">
                            Nobody has been billed for this semester yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <hr />
              <button
                type="button"
                className="btn btn-success"
                onClick={run}
                disabled={running || !preview.to_bill.length}
              >
                {running
                  ? "Raising…"
                  : `Raise ${preview.to_bill.length} invoice${
                      preview.to_bill.length === 1 ? "" : "s"
                    }`}
              </button>
              <small className="d-block text-muted mt-2">
                Each student is notified as their bill is raised. Safe to run
                again later — anyone already billed for this semester is
                skipped, so a student who joins next week just gets picked up
                then.
              </small>
            </>
          )}
        </ListCard>
      )}

      {result && (
        <ListCard title="Raised">
          <p>{result.detail}</p>
          <table className="table table-bordered table-hover">
            <thead className="thead-dark">
              <tr>
                <th>Invoice</th>
                <th>Student</th>
                <th>Due</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {result.invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>
                    <Link to={`/accountant/fees/invoices/${inv.id}`}>
                      {inv.number}
                    </Link>
                  </td>
                  <td>
                    {inv.student_name}
                    <br />
                    <small className="text-muted">{inv.student_roll || "—"}</small>
                  </td>
                  <td>{inv.due_date}</td>
                  <td>{formatMoney(inv.payable)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ListCard>
      )}
    </>
  );
}

export default InvoiceRun;
