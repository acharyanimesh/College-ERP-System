import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import feeAPI from "../../api/fees";
import DepositSlipForm from "../../components/DepositSlipForm";
import { BackButton, ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const STATUS_BADGE = {
  paid: "badge-success",
  due: "badge-info",
  partial: "badge-warning",
  overdue: "badge-danger",
  cancelled: "badge-secondary",
};

const SLIP_BADGE = {
  pending: "badge-warning",
  verified: "badge-success",
  rejected: "badge-danger",
};

/**
 * One of the student's own bills, itemised.
 *
 * Shows the whole story rather than just the number: what was charged, what
 * was taken off and why, and every receipt against it. A student who can see
 * how the figure was reached has far less to ask the office about.
 */
function FeeInvoiceDetail() {
  const { invoiceId } = useParams();
  const { addMessage } = useMessages();
  const { data: invoice, reload: reloadInvoice } = useApi(
    () => feeAPI.myInvoice(invoiceId),
    [invoiceId]
  );
  // Slips are fetched across all bills and narrowed here rather than being
  // folded into the invoice payload: they belong to the student, not to the
  // bill, and a rejected one has to survive the bill being settled.
  const { data: allSlips, reload: reloadSlips } = useApi(() => feeAPI.mySlips());
  const [submitting, setSubmitting] = useState(false);

  usePageHeader({
    title: invoice ? `Invoice ${invoice.number}` : "Invoice",
    breadcrumb: [{ text: "My Fees" }],
  });

  const slips = (allSlips || []).filter(
    (s) => String(s.invoice_id) === String(invoiceId)
  );

  const submitSlip = async (fields) => {
    setSubmitting(true);
    try {
      await feeAPI.submitSlip(invoiceId, fields);
      addMessage(
        "Slip submitted. The accounts office will check it against the bank " +
          "statement — the bill stays as it is until they do.",
        "success"
      );
      reloadSlips();
    } catch (err) {
      const data = err.response?.data || {};
      addMessage(
        data.detail ||
          data.amount?.[0] ||
          data.image?.[0] ||
          data.reference?.[0] ||
          data.bank_name?.[0] ||
          data.deposited_on?.[0] ||
          "Could not submit the slip.",
        "danger"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const withdrawSlip = async (slip) => {
    if (
      !window.confirm(
        `Withdraw the slip ${slip.reference}? You can submit it again ` +
          `afterwards if you need to.`
      )
    )
      return;
    try {
      await feeAPI.withdrawSlip(slip.id);
      addMessage("Slip withdrawn.", "success");
      reloadSlips();
      reloadInvoice();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not withdraw the slip.",
        "danger"
      );
    }
  };

  if (!invoice) return null;

  const canSubmitSlip = !invoice.is_cancelled && Number(invoice.balance) > 0;

  return (
    <>
      <ListCard
        dark
        title={invoice.number}
        action={<BackButton to="/student/fees/">Back to My Fees</BackButton>}
      >
        <dl className="row">
          <dt className="col-sm-3">Class</dt>
          <dd className="col-sm-9">
            {invoice.course_name} · Semester {invoice.semester} ·{" "}
            {invoice.session_name}
          </dd>
          <dt className="col-sm-3">Issued</dt>
          <dd className="col-sm-9">{invoice.issued_date}</dd>
          <dt className="col-sm-3">Due</dt>
          <dd className="col-sm-9">
            {invoice.due_date}
            {invoice.days_overdue > 0 && (
              <span className="badge badge-danger ml-2">
                {invoice.days_overdue} days late
              </span>
            )}
          </dd>
          <dt className="col-sm-3">Status</dt>
          <dd className="col-sm-9">
            <span
              className={`badge ${STATUS_BADGE[invoice.status] || "badge-info"}`}
            >
              {invoice.status}
            </span>
          </dd>
          <dt className="col-sm-3">Still to pay</dt>
          <dd className="col-sm-9 font-weight-bold">
            {formatMoney(invoice.balance)}
          </dd>
        </dl>

        {invoice.is_cancelled && (
          <div className="alert alert-secondary mb-0">
            <strong>This bill was withdrawn.</strong>
            {invoice.cancel_reason ? ` ${invoice.cancel_reason}` : ""} You do
            not owe anything against it.
          </div>
        )}
      </ListCard>

      <ListCard title="What you were charged">
        <table className="table table-bordered">
          <tbody>
            {invoice.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.head_name}</td>
                <td className="text-right">{formatMoney(line.amount)}</td>
              </tr>
            ))}
            <tr>
              <td className="font-weight-bold">Total charged</td>
              <td className="text-right font-weight-bold">
                {formatMoney(invoice.gross)}
              </td>
            </tr>
            {invoice.adjustments.map((adj) => (
              <tr key={adj.id}>
                <td>
                  {adj.kind_display}
                  {adj.reason && (
                    <>
                      {" — "}
                      <small className="text-muted">{adj.reason}</small>
                    </>
                  )}
                </td>
                <td
                  className={`text-right ${
                    Number(adj.amount) < 0 ? "text-success" : "text-danger"
                  }`}
                >
                  {formatMoney(adj.amount)}
                </td>
              </tr>
            ))}
            <tr>
              <td className="font-weight-bold">Payable</td>
              <td className="text-right font-weight-bold">
                {formatMoney(invoice.payable)}
              </td>
            </tr>
            <tr>
              <td>Paid</td>
              <td className="text-right">−{formatMoney(invoice.paid)}</td>
            </tr>
            <tr className="table-active">
              <td className="font-weight-bold">Balance</td>
              <td className="text-right font-weight-bold">
                {formatMoney(invoice.balance)}
              </td>
            </tr>
          </tbody>
        </table>
      </ListCard>

      <ListCard
        title="My Receipts"
        action={
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => window.print()}
          >
            <i className="fas fa-print me-1"></i> Print
          </button>
        }
      >
        <table className="table table-bordered table-hover">
          <thead className="thead-dark">
            <tr>
              <th>Receipt</th>
              <th>Received</th>
              <th>Mode</th>
              <th>Reference</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.payments.length ? (
              invoice.payments.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/student/receipts/${p.id}`}>{p.receipt_no}</Link>
                  </td>
                  <td>{p.received_on}</td>
                  <td>{p.mode_display}</td>
                  <td>{p.reference || "—"}</td>
                  <td>{formatMoney(p.amount)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="text-center">
                  You haven&apos;t paid anything against this bill yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </ListCard>

      {slips.length > 0 && (
        <ListCard title="Bank Deposits I've Submitted">
          <table className="table table-bordered">
            <thead className="thead-dark">
              <tr>
                <th>Slip</th>
                <th>Deposited</th>
                <th>Amount</th>
                <th>State</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {slips.map((slip) => (
                <tr key={slip.id}>
                  <td>
                    {slip.reference}
                    <br />
                    <small className="text-muted">{slip.bank_name}</small>
                  </td>
                  <td>{slip.deposited_on}</td>
                  <td>{formatMoney(slip.amount)}</td>
                  <td>
                    <span
                      className={`badge ${SLIP_BADGE[slip.status] || "badge-info"}`}
                    >
                      {slip.status_display}
                    </span>
                    {/* The rejection reason is the only thing that tells a
                        student what to do next, so it is never hidden. */}
                    {slip.review_note && (
                      <>
                        <br />
                        <small className="text-muted">{slip.review_note}</small>
                      </>
                    )}
                    {slip.receipt_no && (
                      <>
                        <br />
                        <small>
                          <Link to={`/student/receipts/${slip.payment_id}`}>
                            Receipt {slip.receipt_no}
                          </Link>
                        </small>
                      </>
                    )}
                  </td>
                  <td className="text-nowrap">
                    {slip.image_url && (
                      <a
                        className="btn btn-sm btn-secondary mr-1"
                        href={slip.image_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        View
                      </a>
                    )}
                    {slip.status === "pending" && (
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => withdrawSlip(slip)}
                      >
                        Withdraw
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ListCard>
      )}

      {canSubmitSlip && (
        <ListCard title="Paid this into the bank?">
          <DepositSlipForm
            invoice={invoice}
            onSubmit={submitSlip}
            submitting={submitting}
          />
        </ListCard>
      )}
    </>
  );
}

export default FeeInvoiceDetail;
