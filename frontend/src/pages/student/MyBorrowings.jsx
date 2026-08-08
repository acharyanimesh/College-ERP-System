import { Link } from "react-router-dom";
import libraryAPI from "../../api/library";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const STATUS_BADGE = {
  pending: "badge-warning",
  approved: "badge-info",
  issued: "badge-success",
  returned: "badge-secondary",
  rejected: "badge-danger",
  cancelled: "badge-secondary",
};

const RENEWAL_BADGE = {
  requested: "badge-warning",
  granted: "badge-success",
  declined: "badge-danger",
};

/**
 * My Borrowings — every request this student has made, where it got to, and
 * the two things they can do about a book in their bag: ask for one more week,
 * or settle the fine if it came back late.
 */
function MyBorrowings() {
  usePageHeader({
    title: "My Borrowings",
    breadcrumb: [{ text: "Library" }, { text: "My Borrowings" }],
  });
  const { addMessage } = useMessages();
  const { data: requests, reload } = useApi(() => libraryAPI.mine());
  const { data: fines, reload: reloadFines } = useApi(() => libraryAPI.myFines());

  const cancel = async (req) => {
    if (!window.confirm(`Withdraw your request for "${req.book_name}"?`)) return;
    try {
      await libraryAPI.cancel(req.id);
      addMessage("Request withdrawn.", "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not withdraw the request.",
        "danger"
      );
    }
  };

  const requestRenewal = async (req) => {
    const reason = window.prompt(
      `Ask the librarian to renew "${req.book_name}" for one more week.\n\n` +
        `A loan can only be renewed once — after that it has to come back ` +
        `before you can borrow it again.\n\nReason (optional):`,
      ""
    );
    // prompt returns null on Cancel; "" is a legitimate empty reason.
    if (reason === null) return;
    try {
      await libraryAPI.requestRenewal(req.id, reason);
      addMessage("Renewal requested. The librarian will decide on it.", "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not request the renewal.",
        "danger"
      );
    }
  };

  const active = requests?.filter((r) =>
    ["pending", "approved", "issued"].includes(r.status)
  );
  const overdue = active?.filter((r) => r.days_overdue > 0) || [];
  const unpaid = requests?.filter((r) => r.fine_outstanding > 0) || [];
  const unpaidTotal = unpaid.reduce((sum, r) => sum + r.fine_outstanding, 0);

  return (
    <>
      <ListCard
        dark
        title="My Borrowings"
        action={
          <Link to="/student/viewbooks/" className="btn btn-sm btn-secondary">
            <i className="fas fa-book"></i> Browse Library
          </Link>
        }
        scrollBody
      >
        {overdue.length > 0 && (
          <div className="alert alert-danger">
            <i className="fas fa-exclamation-triangle"></i> You have{" "}
            {overdue.length} overdue book{overdue.length === 1 ? "" : "s"}. Return{" "}
            {overdue.length === 1 ? "it" : "them"} to the library — Rs. 10 per day
            is adding up, and you can't request anything new until then.
          </div>
        )}

        {unpaidTotal > 0 && (
          <div className="alert alert-warning">
            <i className="fas fa-money-bill-wave"></i> You owe{" "}
            <strong>Rs. {unpaidTotal}</strong> in library fines. Pay in cash at
            the library desk — the librarian records it and you'll get a receipt
            number here.
          </div>
        )}

        <table className="table table-bordered table-hover" style={{ minWidth: 1000 }}>
          <thead className="thead-dark">
            <tr>
              <th>#</th>
              <th>Book</th>
              <th>Status</th>
              <th>Due</th>
              <th>Renewal</th>
              <th>Fine</th>
              <th>Librarian's Note</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {!requests?.length && (
              <tr>
                <td colSpan={8} className="text-center">
                  You haven't requested any books yet.{" "}
                  <Link to="/student/viewbooks/">Browse the library</Link>.
                </td>
              </tr>
            )}
            {requests?.map((req, i) => (
              <tr key={req.id}>
                <td>{i + 1}</td>
                <td>
                  {req.book_name}
                  <br />
                  <small className="text-muted">
                    {req.book_author} · requested {req.requested_at}
                  </small>
                </td>
                <td>
                  <span className={`badge ${STATUS_BADGE[req.status]}`}>
                    {req.status_display}
                  </span>
                </td>
                <td>
                  {req.due_date || <span className="text-muted">—</span>}
                  {req.due_date_before_renewal && (
                    <>
                      <br />
                      <small className="text-muted">
                        was {req.due_date_before_renewal}
                      </small>
                    </>
                  )}
                  {req.days_overdue > 0 && (
                    <>
                      <br />
                      <small className="text-danger">
                        {req.days_overdue} day{req.days_overdue === 1 ? "" : "s"} late
                      </small>
                    </>
                  )}
                </td>
                <td>
                  {req.renewal_state === "none" ? (
                    <span className="text-muted">—</span>
                  ) : (
                    <>
                      <span className={`badge ${RENEWAL_BADGE[req.renewal_state]}`}>
                        {req.renewal_state_display}
                      </span>
                      {req.renewal_librarian_note && (
                        <>
                          <br />
                          <small className="text-muted">
                            {req.renewal_librarian_note}
                          </small>
                        </>
                      )}
                    </>
                  )}
                </td>
                <td>
                  {req.fine ? (
                    <span
                      className={`badge ${
                        req.fine_settled ? "badge-secondary" : "badge-danger"
                      }`}
                    >
                      Rs. {req.fine} {req.fine_settled ? "· settled" : "· unpaid"}
                    </span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td style={{ maxWidth: 200, wordWrap: "break-word" }}>
                  {req.librarian_note || <span className="text-muted">—</span>}
                </td>
                <td className="text-nowrap">
                  {req.status === "pending" && (
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => cancel(req)}
                    >
                      Withdraw
                    </button>
                  )}
                  {req.can_request_renewal && (
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => requestRenewal(req)}
                    >
                      <i className="fas fa-clock"></i> Renew
                    </button>
                  )}
                  {req.status === "issued" &&
                    req.renewal_state === "granted" && (
                      <small className="text-muted">Already renewed</small>
                    )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ListCard>

      <FineReceipts fines={fines} onReload={reloadFines} />
    </>
  );
}

/**
 * The student's copy of the cash record. These rows are written once at the
 * desk and can never be edited or deleted, so this is a statement rather than
 * a list with actions on it.
 */
function FineReceipts({ fines }) {
  if (!fines?.length) return null;

  const paid = fines
    .filter((f) => f.kind === "paid")
    .reduce((sum, f) => sum + f.amount, 0);

  return (
    <ListCard title="Fine Receipts">
      <p className="text-muted">
        Fines you have settled at the library desk. Rs. {paid} paid in total.
        These are permanent records and can't be changed.
      </p>
      <table className="table table-bordered" style={{ minWidth: 760 }}>
        <thead className="thead-dark">
          <tr>
            <th>Receipt No.</th>
            <th>Book</th>
            <th>Days Late</th>
            <th>Amount</th>
            <th>Outcome</th>
            <th>Received By</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {fines.map((f) => (
            <tr key={f.id}>
              <td>
                <code>{f.receipt_no}</code>
              </td>
              <td>{f.book_name}</td>
              <td>{f.days_late}</td>
              <td>Rs. {f.amount}</td>
              <td>
                <span
                  className={`badge ${
                    f.kind === "paid" ? "badge-success" : "badge-info"
                  }`}
                >
                  {f.kind_display}
                </span>
                {f.note && (
                  <>
                    <br />
                    <small className="text-muted">{f.note}</small>
                  </>
                )}
              </td>
              <td>{f.collected_by || <span className="text-muted">—</span>}</td>
              <td>{f.collected_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default MyBorrowings;
