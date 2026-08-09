import financeAPI from "../../api/finance";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { rs } from "../../constants/money";
import { usePageHeader } from "../../layouts/Layout";

/**
 * Library Fines (read-only): the accountant's window onto the college's other
 * money stream. The librarian collects these at their own desk — here they are
 * only for keeping the books straight.
 */
function LibraryFines() {
  usePageHeader({
    title: "Library Fines",
    breadcrumb: [{ text: "Library Fines" }],
  });
  const { data } = useApi(() => financeAPI.getLibraryFines());
  const d = data || {};

  return (
    <>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon success">
            <i className="fas fa-hand-holding-usd"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--success-color)" }}>
              {rs(d.total_collected)}
            </div>
            <p className="stat-label">Fines Collected</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon danger">
            <i className="fas fa-exclamation-triangle"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--danger-color)" }}>
              {rs(d.total_outstanding)}
            </div>
            <p className="stat-label">Outstanding On Overdue Loans</p>
          </div>
        </div>
      </div>

      {d.outstanding_loans?.length > 0 && (
        <ListCard title="Owed On Loans Currently Out">
          <table className="table table-bordered table-hover">
            <thead className="thead-dark">
              <tr>
                <th>Student</th>
                <th>Book</th>
                <th>Days Overdue</th>
                <th>Fine</th>
              </tr>
            </thead>
            <tbody>
              {d.outstanding_loans.map((l, i) => (
                <tr key={i}>
                  <td>{l.student_name}</td>
                  <td>{l.book_name}</td>
                  <td>
                    <span className="badge badge-danger">{l.days_overdue}d</span>
                  </td>
                  <td>{rs(l.fine)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ListCard>
      )}

      <ListCard title="Fine Receipts" scrollBody>
        <table className="table table-bordered table-hover" style={{ minWidth: 780 }}>
          <thead className="thead-dark">
            <tr>
              <th>Receipt</th>
              <th>Student</th>
              <th>Book</th>
              <th>Days Late</th>
              <th>Amount</th>
              <th>Kind</th>
              <th>Collected By</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {d.receipts?.length ? (
              d.receipts.map((f) => (
                <tr key={f.id}>
                  <td>{f.receipt_no}</td>
                  <td>
                    {f.student_name}
                    <br />
                    <small className="text-muted">{f.student_roll || "—"}</small>
                  </td>
                  <td>{f.book_name}</td>
                  <td>{f.days_late}</td>
                  <td>{rs(f.amount)}</td>
                  <td>
                    <span
                      className={`badge ${
                        f.kind === "waived" ? "badge-secondary" : "badge-success"
                      }`}
                    >
                      {f.kind_display}
                    </span>
                  </td>
                  <td>{f.collected_by || "—"}</td>
                  <td>{f.collected_at}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={8} className="text-center text-muted">
                  No fine receipts yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </ListCard>
    </>
  );
}

export default LibraryFines;
