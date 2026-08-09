import { formatMoney } from "../constants/money";

/**
 * A fee receipt, laid out to be printed and handed over.
 *
 * Everything here is read back off the saved record rather than the form that
 * created it — the paper and the ledger have to agree, and the ledger is the
 * one that is right.
 */
export default function Receipt({ payment, onPrint }) {
  if (!payment) return null;
  return (
    <div className="receipt">
      <div className="d-flex justify-content-between align-items-start">
        <div>
          <h4 className="mb-0">Fee Receipt</h4>
          <div className="text-muted">{payment.receipt_no}</div>
        </div>
        {onPrint && (
          <button
            type="button"
            className="btn btn-secondary btn-sm d-print-none"
            onClick={onPrint}
          >
            <i className="fas fa-print me-1"></i> Print
          </button>
        )}
      </div>

      <hr />

      <dl className="row mb-0">
        {payment.student_name && (
          <>
            <dt className="col-sm-4">Received from</dt>
            <dd className="col-sm-8">
              {payment.student_name}
              {payment.student_roll ? ` · ${payment.student_roll}` : ""}
            </dd>
          </>
        )}
        <dt className="col-sm-4">Against invoice</dt>
        <dd className="col-sm-8">{payment.invoice_number}</dd>
        <dt className="col-sm-4">Date</dt>
        <dd className="col-sm-8">{payment.received_on}</dd>
        <dt className="col-sm-4">Mode</dt>
        <dd className="col-sm-8">{payment.mode_display}</dd>
        {payment.reference && (
          <>
            <dt className="col-sm-4">Reference</dt>
            <dd className="col-sm-8">{payment.reference}</dd>
          </>
        )}
        <dt className="col-sm-4">Received by</dt>
        <dd className="col-sm-8">{payment.collected_by_name || "—"}</dd>
        {payment.note && (
          <>
            <dt className="col-sm-4">Note</dt>
            <dd className="col-sm-8">{payment.note}</dd>
          </>
        )}
        <dt className="col-sm-4 h5">Amount</dt>
        <dd className="col-sm-8 h5">{formatMoney(payment.amount)}</dd>
      </dl>
    </div>
  );
}
