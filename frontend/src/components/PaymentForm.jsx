import { useState } from "react";
import { formatMoney } from "../constants/money";

/**
 * The counter's payment form, shared by the Collect Payment desk screen and
 * the invoice detail page so a payment is taken the same way from either.
 *
 * Deliberately offers cash / cheque / bank only. An online payment exists
 * because a gateway confirmed it, and letting the desk type one in by hand
 * would put an unverifiable row in the ledger beside the verified ones — the
 * server refuses it too.
 */
const MODES = [
  { value: "cash", label: "Cash" },
  { value: "cheque", label: "Cheque" },
  { value: "bank", label: "Bank deposit" },
];

const REFERENCE_REQUIRED = ["cheque", "bank"];

const today = () => new Date().toISOString().slice(0, 10);

export default function PaymentForm({ invoice, onSubmit, submitting }) {
  const [fields, setFields] = useState({
    amount: String(invoice.balance ?? ""),
    mode: "cash",
    reference: "",
    received_on: today(),
    note: "",
  });

  const setField = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  const needsReference = REFERENCE_REQUIRED.includes(fields.mode);
  const over = Number(fields.amount) > Number(invoice.balance);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(fields);
      }}
    >
      <div className="row">
        <div className="col-md-4 form-group">
          <label>Amount (Rs.)</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            className={`form-control ${over ? "is-invalid" : ""}`}
            value={fields.amount}
            onChange={(e) => setField("amount", e.target.value)}
            required
          />
          <small className="text-muted">
            {formatMoney(invoice.balance)} outstanding. Part payments are fine.
          </small>
          {over && (
            <div className="invalid-feedback d-block">
              That is more than the {formatMoney(invoice.balance)} still owed.
            </div>
          )}
        </div>
        <div className="col-md-4 form-group">
          <label>Mode</label>
          <select
            className="form-control"
            value={fields.mode}
            onChange={(e) => setField("mode", e.target.value)}
          >
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
        <div className="col-md-4 form-group">
          <label>Received on</label>
          <input
            type="date"
            max={today()}
            className="form-control"
            value={fields.received_on}
            onChange={(e) => setField("received_on", e.target.value)}
          />
        </div>
      </div>

      <div className="row">
        <div className="col-md-5 form-group">
          <label>
            {needsReference ? "Cheque / deposit slip number" : "Reference"}
            {needsReference && <span className="text-danger"> *</span>}
          </label>
          <input
            className="form-control"
            value={fields.reference}
            onChange={(e) => setField("reference", e.target.value)}
            required={needsReference}
            placeholder={needsReference ? "e.g. 004521" : "Optional"}
          />
          {needsReference && (
            <small className="text-muted">
              What the bank statement gets matched against later.
            </small>
          )}
        </div>
        <div className="col-md-7 form-group">
          <label>Note</label>
          <input
            className="form-control"
            value={fields.note}
            onChange={(e) => setField("note", e.target.value)}
            placeholder="Optional"
          />
        </div>
      </div>

      <button className="btn btn-success" disabled={submitting || over}>
        <i className="fas fa-cash-register me-1"></i>
        {submitting ? "Recording…" : "Record the payment"}
      </button>
      <small className="d-block text-muted mt-2">
        This writes a permanent receipt. It can never be edited or deleted — a
        mistake is corrected with an adjustment on the bill.
      </small>
    </form>
  );
}
