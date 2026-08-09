import { useMemo, useState } from "react";
import financeAPI from "../../api/finance";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { rs } from "../../constants/money";
import { usePageHeader } from "../../layouts/Layout";

/** Every fee receipt taken at the desk, searchable and filterable by course. */
function Payments() {
  usePageHeader({
    title: "Fee Payments",
    breadcrumb: [{ text: "Fee Payments" }],
  });
  const [query, setQuery] = useState("");
  const [course, setCourse] = useState("");

  const { data: payments } = useApi(() => financeAPI.getPayments());

  const courses = useMemo(() => {
    const seen = new Map();
    (payments || []).forEach((p) => {
      if (p.student_course && !seen.has(p.student_course)) {
        seen.set(p.student_course, p.student_course);
      }
    });
    return [...seen.keys()].sort();
  }, [payments]);

  const visible = useMemo(() => {
    let rows = payments || [];
    if (course) rows = rows.filter((p) => p.student_course === course);
    const q = query.toLowerCase().trim();
    if (q) {
      rows = rows.filter(
        (p) =>
          p.receipt_no.toLowerCase().includes(q) ||
          p.student_name.toLowerCase().includes(q) ||
          (p.student_roll || "").toLowerCase().includes(q)
      );
    }
    return rows;
  }, [payments, query, course]);

  const total = visible.reduce((sum, p) => sum + p.amount, 0);

  return (
    <ListCard
      title="Fee Payments"
      action={<span className="badge badge-success">{rs(total)} shown</span>}
      scrollBody
    >
      <div className="d-flex gap-2 flex-wrap mb-3">
        <input
          type="text"
          className="form-control"
          style={{ maxWidth: 320 }}
          placeholder="Search receipt, student or roll…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="form-control"
          style={{ maxWidth: 200 }}
          value={course}
          onChange={(e) => setCourse(e.target.value)}
        >
          <option value="">All courses</option>
          {courses.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 820 }}>
        <thead className="thead-dark">
          <tr>
            <th>Receipt</th>
            <th>Student</th>
            <th>Course</th>
            <th>Sem</th>
            <th>Amount</th>
            <th>Method</th>
            <th>Collected By</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {visible.length ? (
            visible.map((p) => (
              <tr key={p.id}>
                <td>{p.receipt_no}</td>
                <td>
                  {p.student_name}
                  <br />
                  <small className="text-muted">{p.student_roll || "—"}</small>
                </td>
                <td>{p.student_course}</td>
                <td>{p.semester}</td>
                <td>{rs(p.amount)}</td>
                <td>{p.method_display}</td>
                <td>{p.collected_by || "—"}</td>
                <td>{p.collected_at}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={8} className="text-center text-muted">
                No receipts match.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </ListCard>
  );
}

export default Payments;
