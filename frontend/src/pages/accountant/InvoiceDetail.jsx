import { useState } from "react";
import { useParams } from "react-router-dom";
import feeAPI from "../../api/fees";
import Modal from "../../components/Modal";
import { BackButton, ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const ADJUSTMENT_KINDS = [
  { value: "scholarship", label: "Scholarship (reduces the bill)" },
  { value: "discount", label: "Discount (reduces the bill)" },
  { value: "waiver", label: "Waiver (reduces the bill)" },
  { value: "late_fine", label: "Late fine (adds to the bill)" },
  { value: "correction", label: "Correction (sign as typed)" },
];

const STATUS_BADGE = {
  paid: "badge-success",
  due: "badge-info",
  partial: "badge-warning",
  overdue: "badge-danger",
  cancelled: "badge-secondary",
};

/** One bill, with everything behind its balance and the two things the
 *  office can do to it. */
function InvoiceDetail() {
  const { invoiceId } = useParams();
  const { addMessage } = useMessages();
  const { data: invoice, reload } = useApi(
    () => feeAPI.getInvoice(invoiceId),
    [invoiceId]
  );

  const [adjusting, setAdjusting] = useState(false);
  const [adjustment, setAdjustment] = useState({
    kind: "scholarship",
    amount: "",
    reason: "",
  });
  const [cancelling, setCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  usePageHeader({
    title: invoice ? `Invoice ${invoice.number}` : "Invoice",
    breadcrumb: [{ text: "Fee Invoices" }],
  });

  if (!invoice) return null;

  const submitAdjustment = async () => {
    try {
      await feeAPI.adjustInvoice(invoiceId, adjustment);
      addMessage("Adjustment recorded.", "success");
      setAdjusting(false);
      setAdjustment({ kind: "scholarship", amount: "", reason: "" });
      reload();
    } catch (err) {
      const data = err.response?.data || {};
      addMessage(
        data.detail || data.amount?.[0] || data.reason?.[0] || data.kind?.[0] ||
          "Could not record the adjustment.",
        "danger"
      );
    }
  };

  const submitCancel = async () => {
    try {
      await feeAPI.cancelInvoice(invoiceId, cancelReason);
      addMessage("Invoice cancelled.", "success");
      setCancelling(false);
      reload();
    } catch (err) {
      const data = err.response?.data || {};
      addMessage(
        data.detail || data.reason?.[0] || "Could not cancel the invoice.",
        "danger"
      );
    }
  };

  return (
    <>
      <ListCard
        dark
        title={`${invoice.number} · ${invoice.student_name}`}
        action={<BackButton to="/accountant/fees/invoices/">Back to Invoices</BackButton>}
      >
        <dl className="row">
          <dt className="col-sm-3">Student</dt>
          <dd className="col-sm-9">
            {invoice.student_name} · {invoice.student_roll || "—"} ·{" "}
            {invoice.student_email}
          </dd>
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
            <span className={`badge ${STATUS_BADGE[invoice.status] || "badge-info"}`}>
              {invoice.status}
            </span>
            {invoice.is_cancelled && invoice.cancel_reason && (
              <div className="text-muted mt-1">{invoice.cancel_reason}</div>
            )}
          </dd>
        </dl>

        {!invoice.is_cancelled && (
          <>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setAdjusting(true)}
            >
              <i className="fas fa-percent me-1"></i> Add an adjustment
            </button>{" "}
            <button
              type="button"
              className="btn btn-outline-danger btn-sm"
              onClick={() => setCancelling(true)}
            >
              <i className="fas fa-ban me-1"></i> Cancel this invoice
            </button>
          </>
        )}
      </ListCard>

      <ListCard title="What this bill comes to">
        <table className="table table-bordered">
          <tbody>
            {invoice.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.head_name}</td>
                <td className="text-right">{formatMoney(line.amount)}</td>
              </tr>
            ))}
            <tr>
              <td className="font-weight-bold">Gross</td>
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
                  <br />
                  <small className="text-muted">
                    {adj.created_by_name || "—"} · {adj.created_at}
                  </small>
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

      <ListCard title="Receipts">
        <table className="table table-bordered table-hover">
          <thead className="thead-dark">
            <tr>
              <th>Receipt</th>
              <th>Received</th>
              <th>Mode</th>
              <th>Reference</th>
              <th>Taken by</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.payments.length ? (
              invoice.payments.map((p) => (
                <tr key={p.id}>
                  <td>{p.receipt_no}</td>
                  <td>{p.received_on}</td>
                  <td>{p.mode_display}</td>
                  <td>{p.reference || "—"}</td>
                  <td>{p.collected_by_name || "—"}</td>
                  <td>{formatMoney(p.amount)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="text-center">
                  Nothing has been paid against this bill yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </ListCard>

      <Modal
        show={adjusting}
        onClose={() => setAdjusting(false)}
        header={<h5 className="modal-title">Add an Adjustment</h5>}
        footer={
          <button type="button" className="btn btn-primary" onClick={submitAdjustment}>
            Record it
          </button>
        }
      >
        <div className="form-group">
          <label>Kind</label>
          <select
            className="form-control"
            value={adjustment.kind}
            onChange={(e) =>
              setAdjustment((a) => ({ ...a, kind: e.target.value }))
            }
          >
            {ADJUSTMENT_KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Amount (Rs.)</label>
          <input
            type="number"
            step="0.01"
            className="form-control"
            value={adjustment.amount}
            onChange={(e) =>
              setAdjustment((a) => ({ ...a, amount: e.target.value }))
            }
            placeholder="5000"
          />
          <small className="text-muted">
            Type a plain positive number — the kind decides whether it adds to
            the bill or takes away.
          </small>
        </div>
        <div className="form-group">
          <label>Reason</label>
          <textarea
            className="form-control"
            rows={2}
            value={adjustment.reason}
            onChange={(e) =>
              setAdjustment((a) => ({ ...a, reason: e.target.value }))
            }
          />
        </div>
        <div className="alert alert-warning mb-0">
          This record can never be edited or deleted. A mistake is corrected by
          writing the opposite adjustment, so the bill always shows how it got
          to its number.
        </div>
      </Modal>

      <Modal
        show={cancelling}
        onClose={() => setCancelling(false)}
        header={<h5 className="modal-title">Cancel This Invoice</h5>}
        footer={
          <button type="button" className="btn btn-danger" onClick={submitCancel}>
            Cancel the invoice
          </button>
        }
      >
        <div className="form-group">
          <label>Why is this bill being withdrawn?</label>
          <textarea
            className="form-control"
            rows={3}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
        </div>
        <p className="text-muted mb-0">
          The invoice stays on the record with this reason attached — a
          withdrawn charge is a thing that happened, not a thing to delete.
        </p>
      </Modal>
    </>
  );
}

export default InvoiceDetail;
