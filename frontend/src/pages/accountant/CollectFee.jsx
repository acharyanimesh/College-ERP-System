import { useMemo, useState } from "react";
import financeAPI from "../../api/finance";
import useApi from "../../hooks/useApi";
import { rs, PAYMENT_METHODS } from "../../constants/money";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const STATUS_BADGE = {
  paid: "badge-success",
  partial: "badge-warning",
  unpaid: "badge-danger",
  unbilled: "badge-secondary",
};
const STATUS_LABEL = {
  paid: "Paid up",
  partial: "Part-paid",
  unpaid: "Unpaid",
  unbilled: "No fee set",
};

/**
 * Collect Fee: pick a student, see their term dues and receipt history, and
 * take a payment. The left column is the worklist (searchable, outstanding
 * first); the right column is the selected student's ledger + the counter form.
 */
function CollectFee() {
  usePageHeader({
    title: "Collect Fee",
    breadcrumb: [{ text: "Collect Fee" }],
  });
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState({ amount: "", method: "cash", note: "" });
  const [submitting, setSubmitting] = useState(false);

  const { data: students, reload: reloadList } = useApi(() =>
    financeAPI.getStudentFees()
  );
  const { data: detail, reload: reloadDetail } = useApi(
    () => (selectedId ? financeAPI.getStudentFee(selectedId) : Promise.resolve(null)),
    [selectedId]
  );

  const visible = useMemo(() => {
    const list = students || [];
    const q = query.toLowerCase().trim();
    const filtered = q
      ? list.filter(
          (r) =>
            r.student_name.toLowerCase().includes(q) ||
            (r.roll_number || "").toLowerCase().includes(q)
        )
      : list;
    // Outstanding first, then by name — the desk works the debtors.
    return [...filtered].sort(
      (a, b) => b.outstanding - a.outstanding || a.student_name.localeCompare(b.student_name)
    );
  }, [students, query]);

  const select = (row) => {
    setSelectedId(row.student_id);
    setForm({ amount: String(row.outstanding || ""), method: "cash", note: "" });
  };

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  const submit = async (e) => {
    e.preventDefault();
    const amount = parseInt(form.amount, 10);
    if (!amount || amount <= 0) {
      addMessage("Enter an amount greater than zero.", "danger");
      return;
    }
    setSubmitting(true);
    try {
      const result = await financeAPI.recordPayment({
        student: selectedId,
        amount,
        semester: detail?.semester,
        method: form.method,
        note: form.note,
      });
      addMessage(result.detail || "Payment recorded.", "success");
      setForm({ amount: "", method: "cash", note: "" });
      reloadDetail();
      reloadList();
    } catch (err) {
      addMessage(
        err.response?.data?.detail ||
          err.response?.data?.amount?.[0] ||
          "Could not record the payment.",
        "danger"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="row">
      {/* Worklist */}
      <div className="col-lg-5">
        <div className="card card-dark">
          <div className="card-header">
            <h3 className="card-title">Students</h3>
          </div>
          <div className="card-body" style={{ maxHeight: 620, overflowY: "auto" }}>
            <input
              type="text"
              className="form-control mb-3"
              placeholder="Search by name or roll number…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <table className="table table-hover">
              <thead>
                <tr>
                  <th>Student</th>
                  <th className="text-end">Outstanding</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr
                    key={r.student_id}
                    style={{ cursor: "pointer" }}
                    className={selectedId === r.student_id ? "table-active" : ""}
                    onClick={() => select(r)}
                  >
                    <td>
                      {r.student_name}
                      <br />
                      <small className="text-muted">
                        {r.roll_number || "—"} · {r.course_short_name} · Sem {r.semester}
                      </small>
                    </td>
                    <td className="text-end">
                      {r.outstanding ? (
                        <span className="badge badge-danger">{rs(r.outstanding)}</span>
                      ) : (
                        <span className={`badge ${STATUS_BADGE[r.status]}`}>
                          {STATUS_LABEL[r.status]}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {!visible.length && (
                  <tr>
                    <td colSpan={2} className="text-center text-muted">
                      No students match.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Selected student */}
      <div className="col-lg-7">
        {!detail ? (
          <div className="card">
            <div className="card-body text-center text-muted py-5">
              <i className="fas fa-hand-pointer fa-2x mb-3"></i>
              <p>Select a student to record a payment.</p>
            </div>
          </div>
        ) : (
          <>
            <div className="card card-dark">
              <div className="card-header">
                <h3 className="card-title">{detail.student_name}</h3>
              </div>
              <div className="card-body">
                <dl className="row mb-0">
                  <dt className="col-sm-4">Course / Semester</dt>
                  <dd className="col-sm-8">
                    {detail.course_short_name} · Semester {detail.semester}
                  </dd>
                  <dt className="col-sm-4">Term fee</dt>
                  <dd className="col-sm-8">{rs(detail.expected)}</dd>
                  <dt className="col-sm-4">Paid this term</dt>
                  <dd className="col-sm-8">{rs(detail.paid)}</dd>
                  <dt className="col-sm-4">Outstanding</dt>
                  <dd className="col-sm-8">
                    {detail.outstanding ? (
                      <span className="badge badge-danger">{rs(detail.outstanding)}</span>
                    ) : (
                      <span className="badge badge-success">Cleared</span>
                    )}
                  </dd>
                </dl>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Record a Payment</h3>
              </div>
              <form onSubmit={submit}>
                <div className="card-body">
                  {detail.status === "unbilled" && (
                    <div className="alert alert-warning">
                      No fee is set for {detail.course_short_name} Semester{" "}
                      {detail.semester} yet. You can still take a payment, but set
                      the amount under <strong>Fee Structure</strong> so the
                      balance reads correctly.
                    </div>
                  )}
                  <div className="row g-3">
                    <div className="form-group col-md-4">
                      <label htmlFor="id_amount">Amount (Rs.):</label>
                      <input
                        id="id_amount"
                        type="number"
                        min="1"
                        className="form-control"
                        value={form.amount}
                        onChange={(e) => setField("amount", e.target.value)}
                        required
                      />
                    </div>
                    <div className="form-group col-md-4">
                      <label htmlFor="id_method">Method:</label>
                      <select
                        id="id_method"
                        className="form-control"
                        value={form.method}
                        onChange={(e) => setField("method", e.target.value)}
                      >
                        {PAYMENT_METHODS.map((m) => (
                          <option key={m.value} value={m.value}>
                            {m.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="form-group col-md-4">
                      <label htmlFor="id_note">Note (optional):</label>
                      <input
                        id="id_note"
                        type="text"
                        className="form-control"
                        value={form.note}
                        onChange={(e) => setField("note", e.target.value)}
                      />
                    </div>
                  </div>
                </div>
                <div className="card-footer">
                  <button
                    type="submit"
                    className="btn btn-success w-100"
                    disabled={submitting}
                  >
                    <i className="fas fa-cash-register me-2"></i>
                    {submitting ? "Recording…" : "Record Payment & Issue Receipt"}
                  </button>
                </div>
              </form>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Receipt History</h3>
              </div>
              <div className="card-body">
                <table className="table table-bordered table-hover">
                  <thead className="thead-dark">
                    <tr>
                      <th>Receipt</th>
                      <th>Sem</th>
                      <th>Amount</th>
                      <th>Method</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.payments?.length ? (
                      detail.payments.map((p) => (
                        <tr key={p.id}>
                          <td>{p.receipt_no}</td>
                          <td>{p.semester}</td>
                          <td>{rs(p.amount)}</td>
                          <td>{p.method_display}</td>
                          <td>{p.collected_on}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="text-center text-muted">
                          No payments on record for this student.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default CollectFee;
