import { useState } from "react";
import { Link } from "react-router-dom";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const SLIP_BADGE = {
  pending: "badge-warning",
  verified: "badge-success",
  rejected: "badge-danger",
};

/**
 * Bank deposits students say they have made, waiting on the office.
 *
 * A work queue, so it opens on what is still unanswered and in the order the
 * claims arrived. Verifying writes a real receipt against the bill, which is
 * why the amount is editable here: the desk is reading the bank statement and
 * the student was reading a photograph, and when they disagree the statement
 * is what the ledger has to follow.
 */
function SlipQueue() {
  usePageHeader({
    title: "Bank Deposits",
    breadcrumb: [{ text: "Collection" }, { text: "Bank Deposits" }],
  });
  const { addMessage } = useMessages();

  const [filters, setFilters] = useState({ status: "pending", q: "" });
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [amounts, setAmounts] = useState({});

  const { data, reload } = useApi(
    () =>
      feeAPI.getSlips({
        status: filters.status,
        q: filters.q || undefined,
      }),
    [filters.status, filters.q]
  );

  const verify = async (slip) => {
    const typed = (amounts[slip.id] ?? "").trim();
    const amount = typed || slip.amount;
    if (
      !window.confirm(
        `Verify ${formatMoney(amount)} against ${slip.invoice_number} for ` +
          `${slip.student_name}?\n\nThis writes a permanent receipt. Only do ` +
          `it once you can see the deposit on the bank statement.`
      )
    )
      return;

    setBusyId(slip.id);
    try {
      const result = await feeAPI.verifySlip(slip.id, typed ? { amount: typed } : {});
      addMessage(
        `Receipt ${result.payment.receipt_no} — ${formatMoney(
          result.payment.amount
        )} credited to ${result.slip.invoice_number}.`,
        "success"
      );
      reload();
    } catch (err) {
      const body = err.response?.data || {};
      addMessage(
        body.detail || body.amount?.[0] || "Could not verify the slip.",
        "danger"
      );
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (slip) => {
    const reason = window.prompt(
      `Turn down slip ${slip.reference} from ${slip.student_name}?\n\n` +
        `The reason goes straight to the student, so make it something they ` +
        `can act on.\n\nReason:`,
      ""
    );
    if (reason === null) return;
    if (!reason.trim()) {
      addMessage("A rejected slip needs a reason the student can act on.", "danger");
      return;
    }

    setBusyId(slip.id);
    try {
      await feeAPI.rejectSlip(slip.id, reason);
      addMessage(`Slip ${slip.reference} turned down.`, "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail ||
          err.response?.data?.reason?.[0] ||
          "Could not reject the slip.",
        "danger"
      );
    } finally {
      setBusyId(null);
    }
  };

  const slips = data?.slips;

  return (
    <ListCard title="Bank Deposits" scrollBody>
      <div className="row">
        <div className="col-md-4 form-group">
          <select
            className="form-control"
            value={filters.status}
            onChange={(e) =>
              setFilters((f) => ({ ...f, status: e.target.value }))
            }
          >
            <option value="pending">Waiting on us</option>
            <option value="verified">Verified</option>
            <option value="rejected">Turned down</option>
            <option value="all">Everything</option>
          </select>
        </div>
        <div className="col-md-8 form-group">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFilters((f) => ({ ...f, q: query }));
            }}
          >
            <div className="input-group">
              <input
                className="form-control"
                placeholder="Voucher number, bank, invoice, name or roll…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button className="btn btn-primary" type="submit">
                <i className="fas fa-search"></i>
              </button>
            </div>
          </form>
        </div>
      </div>

      <div
        className={`alert ${data?.pending_count ? "alert-warning" : "alert-success"}`}
      >
        <i className="fas fa-inbox"></i>{" "}
        {data?.pending_count
          ? `${data.pending_count} deposit${
              data.pending_count === 1 ? "" : "s"
            } waiting to be checked against the bank statement.`
          : "Nothing is waiting — every slip submitted has been answered."}
      </div>

      <table className="table table-bordered" style={{ minWidth: 1100 }}>
        <thead className="thead-dark">
          <tr>
            <th>Student</th>
            <th>Invoice</th>
            <th>Slip</th>
            <th>Claimed</th>
            <th>State</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {!slips?.length && (
            <tr>
              <td colSpan={6} className="text-center">
                Nothing here.
              </td>
            </tr>
          )}
          {slips?.map((slip) => (
            <tr key={slip.id}>
              <td>
                {slip.student_name}
                <br />
                <small className="text-muted">{slip.student_roll || "—"}</small>
              </td>
              <td>
                <Link to={`/accountant/fees/invoices/${slip.invoice_id}`}>
                  {slip.invoice_number}
                </Link>
                <br />
                <small className="text-muted">
                  {formatMoney(slip.invoice_balance)} owed
                </small>
              </td>
              <td>
                {slip.reference}
                <br />
                <small className="text-muted">
                  {slip.bank_name} · {slip.deposited_on}
                </small>
                {slip.note && (
                  <>
                    <br />
                    <small className="text-muted">{slip.note}</small>
                  </>
                )}
              </td>
              <td>
                {formatMoney(slip.amount)}
                {slip.image_url && (
                  <>
                    <br />
                    <a
                      href={slip.image_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-sm btn-secondary mt-1"
                    >
                      <i className="fas fa-image me-1"></i> See slip
                    </a>
                  </>
                )}
              </td>
              <td>
                <span
                  className={`badge ${SLIP_BADGE[slip.status] || "badge-info"}`}
                >
                  {slip.status_display}
                </span>
                {slip.reviewed_by_name && (
                  <>
                    <br />
                    <small className="text-muted">
                      {slip.reviewed_by_name} · {slip.reviewed_at}
                    </small>
                  </>
                )}
                {slip.review_note && (
                  <>
                    <br />
                    <small className="text-muted">{slip.review_note}</small>
                  </>
                )}
                {slip.receipt_no && (
                  <>
                    <br />
                    <small>Receipt {slip.receipt_no}</small>
                  </>
                )}
              </td>
              <td className="text-nowrap">
                {slip.status === "pending" ? (
                  <>
                    <input
                      className="form-control form-control-sm mb-1"
                      placeholder={`Bank shows (${slip.amount})`}
                      inputMode="decimal"
                      value={amounts[slip.id] ?? ""}
                      onChange={(e) =>
                        setAmounts((a) => ({ ...a, [slip.id]: e.target.value }))
                      }
                    />
                    <button
                      type="button"
                      className="btn btn-sm btn-success mr-1"
                      disabled={busyId === slip.id}
                      onClick={() => verify(slip)}
                    >
                      <i className="fas fa-check"></i> Verify
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger"
                      disabled={busyId === slip.id}
                      onClick={() => reject(slip)}
                    >
                      Turn down…
                    </button>
                  </>
                ) : (
                  <span className="text-muted">Answered</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default SlipQueue;
