import { useState } from "react";
import libraryAPI from "../../api/library";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Library fines: what is still owed on late returns, and the cash book of
 * everything already settled.
 *
 * A fine is only settleable once the book is back — while it is still out the
 * amount grows every day, and there is nothing fixed to take money against.
 * Settling writes a LibraryFine receipt, which is append-only: a mistake is
 * corrected by a second offsetting record, never by editing this one. That is
 * why nothing on the history table below is clickable.
 */
function Fines() {
  usePageHeader({
    title: "Library Fines",
    breadcrumb: [{ text: "Circulation" }, { text: "Fines" }],
  });
  const { addMessage } = useMessages();
  const { data: unsettled, reload: reloadUnsettled } = useApi(() =>
    libraryAPI.getUnsettledFines()
  );
  const { data: ledger, reload: reloadLedger } = useApi(() => libraryAPI.getFines());
  const [busyId, setBusyId] = useState(null);

  const settle = async (loan, paid) => {
    let note = "";
    if (paid) {
      if (
        !window.confirm(
          `Record Rs. ${loan.fine} received in cash from ${loan.student_name} ` +
            `for "${loan.book_name}" (${loan.days_late} days late)?\n\n` +
            `This writes a permanent receipt that cannot be edited or deleted.`
        )
      )
        return;
    } else {
      note = window.prompt(
        `Waive the Rs. ${loan.fine} fine for ${loan.student_name}?\n\n` +
          `This is still recorded permanently — the ledger has to explain the ` +
          `gap as much as it explains the cash.\n\nReason:`,
        ""
      );
      if (note === null) return;
      if (!note.trim()) {
        addMessage("A waived fine needs a reason on the record.", "danger");
        return;
      }
    }

    setBusyId(loan.id);
    try {
      const record = paid
        ? await libraryAPI.collectFine(loan.id, note)
        : await libraryAPI.waiveFine(loan.id, note);
      addMessage(
        `Receipt ${record.receipt_no} recorded — Rs. ${record.amount} ${
          paid ? "collected" : "waived"
        }.`,
        "success"
      );
      reloadUnsettled();
      reloadLedger();
    } catch (err) {
      addMessage(
        err.response?.data?.detail ||
          err.response?.data?.note?.[0] ||
          "Could not record the fine.",
        "danger"
      );
    } finally {
      setBusyId(null);
    }
  };

  const outstanding = (unsettled || []).reduce((sum, l) => sum + l.fine, 0);

  return (
    <>
      <ListCard title="Fines to Settle" scrollBody>
        {outstanding > 0 ? (
          <div className="alert alert-warning">
            <i className="fas fa-money-bill-wave"></i> Rs. {outstanding} owed
            across {unsettled.length} returned book
            {unsettled.length === 1 ? "" : "s"}, at Rs. 10 per late day.
          </div>
        ) : (
          <div className="alert alert-success">
            <i className="fas fa-check-circle"></i> Nothing outstanding — every
            late return has been settled.
          </div>
        )}

        {unsettled?.length > 0 && (
          <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
            <thead className="thead-dark">
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Book</th>
                <th>Due</th>
                <th>Returned</th>
                <th>Days Late</th>
                <th>Fine</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {unsettled.map((loan, i) => (
                <tr key={loan.id}>
                  <td>{i + 1}</td>
                  <td>
                    {loan.student_name}
                    <br />
                    <small className="text-muted">
                      {loan.student_roll || "—"} · {loan.student_course}
                    </small>
                  </td>
                  <td>{loan.book_name}</td>
                  <td>{loan.due_date}</td>
                  <td>{loan.returned_date}</td>
                  <td>
                    <span className="badge badge-danger">{loan.days_late}</span>
                  </td>
                  <td>
                    <strong>Rs. {loan.fine}</strong>
                  </td>
                  <td className="text-nowrap">
                    <button
                      type="button"
                      className="btn btn-sm btn-success mr-1"
                      disabled={busyId === loan.id}
                      onClick={() => settle(loan, true)}
                    >
                      <i className="fas fa-hand-holding-usd"></i> Collect cash
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      disabled={busyId === loan.id}
                      onClick={() => settle(loan, false)}
                    >
                      Waive…
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ListCard>

      <ListCard title="Fine Records (Cash Book)" scrollBody>
        <div className="alert alert-info">
          <i className="fas fa-lock"></i> Rs. {ledger?.total_collected ?? 0}{" "}
          collected and Rs. {ledger?.total_waived ?? 0} waived to date. These
          rows are a financial record of cash taken at the desk — they can't be
          edited or deleted, here or in the Django admin. A mistake is fixed by
          recording a correcting entry, not by changing this one.
        </div>

        <table className="table table-bordered" style={{ minWidth: 1000 }}>
          <thead className="thead-dark">
            <tr>
              <th>Receipt No.</th>
              <th>Student</th>
              <th>Book</th>
              <th>Days Late</th>
              <th>Amount</th>
              <th>Outcome</th>
              <th>Received By</th>
              <th>Recorded</th>
            </tr>
          </thead>
          <tbody>
            {!ledger?.records?.length && (
              <tr>
                <td colSpan={8} className="text-center">
                  No fines have been recorded yet.
                </td>
              </tr>
            )}
            {ledger?.records?.map((f) => (
              <tr key={f.id}>
                <td>
                  <code>{f.receipt_no}</code>
                </td>
                <td>
                  {f.student_name}
                  <br />
                  <small className="text-muted">
                    {f.student_roll || "—"} · {f.student_course}
                  </small>
                </td>
                <td>{f.book_name}</td>
                <td>{f.days_late}</td>
                <td>
                  Rs. {f.amount}
                  <br />
                  <small className="text-muted">@ Rs. {f.rate_per_day}/day</small>
                </td>
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
    </>
  );
}

export default Fines;
