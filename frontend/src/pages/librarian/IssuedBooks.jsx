import { useState } from "react";
import { Link } from "react-router-dom";
import libraryAPI from "../../api/library";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** Issued Books — everything currently out, most overdue first. */
function IssuedBooks() {
  usePageHeader({
    title: "Issued Books",
    breadcrumb: [{ text: "Circulation" }, { text: "Issued Books" }],
  });
  const { addMessage } = useMessages();
  const { data: loans, reload } = useApi(() => libraryAPI.getLoans());
  const [busyId, setBusyId] = useState(null);

  const markReturned = async (loan) => {
    setBusyId(loan.id);
    try {
      await libraryAPI.markReturned(loan.id);
      addMessage(
        loan.fine
          ? `"${loan.book_name}" returned. Fine due: Rs. ${loan.fine}.`
          : `"${loan.book_name}" returned.`,
        "success"
      );
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not record the return.",
        "danger"
      );
    } finally {
      setBusyId(null);
    }
  };

  const decideRenewal = async (loan, grant) => {
    let reason = "";
    if (!grant) {
      reason = window.prompt(
        `Decline the renewal of "${loan.book_name}" for ${loan.student_name}.\n\n` +
          `The student is told your reason, and the original due date stands.\n\nReason:`,
        ""
      );
      if (reason === null) return;
      if (!reason.trim()) {
        addMessage("A reason is required to decline a renewal.", "danger");
        return;
      }
    }
    setBusyId(loan.id);
    try {
      if (grant) {
        await libraryAPI.approveRenewal(loan.id);
        addMessage(`"${loan.book_name}" renewed for one more week.`, "success");
      } else {
        await libraryAPI.rejectRenewal(loan.id, reason);
        addMessage("Renewal declined.", "success");
      }
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not record the decision.",
        "danger"
      );
    } finally {
      setBusyId(null);
    }
  };

  const overdue = loans?.filter((l) => l.days_overdue > 0) || [];
  const finesDue = overdue.reduce((sum, l) => sum + l.fine, 0);
  const renewalRequests =
    loans?.filter((l) => l.renewal_state === "requested") || [];

  return (
    <ListCard title="Issued Books" scrollBody>
      {renewalRequests.length > 0 && (
        <div className="alert alert-info">
          <i className="fas fa-clock"></i> {renewalRequests.length} renewal
          request{renewalRequests.length === 1 ? "" : "s"} waiting. Approving one
          pushes its due date out by 7 days; a loan can only be renewed once.
        </div>
      )}

      {overdue.length > 0 && (
        <div className="alert alert-warning">
          <i className="fas fa-exclamation-triangle"></i> {overdue.length} book
          {overdue.length === 1 ? " is" : "s are"} overdue, Rs. {finesDue} in
          fines accruing at Rs. 10/day. Fines are settled once the book is back
          — see <Link to="/librarian/fines/">Fines</Link>.
        </div>
      )}

      <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Student</th>
            <th>Book</th>
            <th>Issued</th>
            <th>Due</th>
            <th>Overdue</th>
            <th>Renewal</th>
            <th>Fine</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {!loans?.length && (
            <tr>
              <td colSpan={9} className="text-center">
                No books are out at the moment.
              </td>
            </tr>
          )}
          {loans?.map((loan, i) => (
            <tr key={loan.id} className={loan.days_overdue ? "table-danger" : undefined}>
              <td>{i + 1}</td>
              <td>
                {loan.student_name}
                <br />
                <small className="text-muted">
                  {loan.student_roll || "—"} · {loan.student_course}
                </small>
              </td>
              <td>
                {loan.book_name}
                <br />
                <small className="text-muted">{loan.book_isbn}</small>
              </td>
              <td>{loan.issued_date}</td>
              <td>
                {loan.due_date}
                {loan.due_date_before_renewal && (
                  <>
                    <br />
                    <small className="text-muted">
                      renewed from {loan.due_date_before_renewal}
                    </small>
                  </>
                )}
              </td>
              <td>
                {loan.days_overdue ? (
                  <span className="badge badge-danger">
                    {loan.days_overdue} day{loan.days_overdue === 1 ? "" : "s"}
                  </span>
                ) : (
                  <span className="badge badge-success">On time</span>
                )}
              </td>
              <td style={{ maxWidth: 220 }}>
                {loan.renewal_state === "requested" ? (
                  <>
                    {loan.renewal_reason && (
                      <small className="d-block text-muted mb-1">
                        “{loan.renewal_reason}”
                      </small>
                    )}
                    <button
                      type="button"
                      className="btn btn-sm btn-success mr-1"
                      disabled={busyId === loan.id}
                      onClick={() => decideRenewal(loan, true)}
                    >
                      <i className="fas fa-check"></i> +7 days
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      disabled={busyId === loan.id}
                      onClick={() => decideRenewal(loan, false)}
                    >
                      <i className="fas fa-times"></i>
                    </button>
                  </>
                ) : loan.renewal_state === "granted" ? (
                  <span className="badge badge-secondary">
                    Renewed · can't renew again
                  </span>
                ) : loan.renewal_state === "declined" ? (
                  <span className="badge badge-secondary">Declined</span>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
              <td>
                {loan.fine ? (
                  <>
                    Rs. {loan.fine}
                    <br />
                    <small className="text-muted">accruing</small>
                  </>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
              <td>
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  disabled={busyId === loan.id}
                  onClick={() => markReturned(loan)}
                >
                  <i className="fas fa-undo"></i> Mark returned
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default IssuedBooks;
