import { useState } from "react";
import { formatMoney } from "../constants/money";

const TODAY = () => new Date().toISOString().slice(0, 10);

/**
 * The student's claim that they paid a bill into the college's bank.
 *
 * Everything here is worded to make one thing unmissable: submitting this
 * pays nothing. The office has to find the deposit on the bank statement
 * first, and until they do the bill still says the money is owed.
 */
export default function DepositSlipForm({ invoice, onSubmit, submitting }) {
  const [fields, setFields] = useState({
    amount: "",
    deposited_on: TODAY(),
    bank_name: "",
    reference: "",
    note: "",
  });
  const [image, setImage] = useState(null);

  const set = (name, value) => setFields((f) => ({ ...f, [name]: value }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ ...fields, image });
      }}
    >
      <div className="alert alert-info">
        <i className="fas fa-info-circle"></i> This bill still shows{" "}
        <strong>{formatMoney(invoice.balance)}</strong> outstanding, and it will
        keep showing that until the accounts office has matched your deposit
        against the bank statement. Nothing is deducted by uploading a slip.
      </div>

      <div className="row">
        <div className="col-md-4 form-group">
          <label>Amount deposited</label>
          <input
            className="form-control"
            inputMode="decimal"
            placeholder="0.00"
            value={fields.amount}
            onChange={(e) => set("amount", e.target.value)}
            required
          />
        </div>
        <div className="col-md-4 form-group">
          <label>Date on the slip</label>
          <input
            type="date"
            className="form-control"
            max={TODAY()}
            value={fields.deposited_on}
            onChange={(e) => set("deposited_on", e.target.value)}
            required
          />
        </div>
        <div className="col-md-4 form-group">
          <label>Bank</label>
          <input
            className="form-control"
            placeholder="e.g. Nabil Bank"
            value={fields.bank_name}
            onChange={(e) => set("bank_name", e.target.value)}
            required
          />
        </div>
      </div>

      <div className="row">
        <div className="col-md-6 form-group">
          <label>Voucher / deposit slip number</label>
          <input
            className="form-control"
            value={fields.reference}
            onChange={(e) => set("reference", e.target.value)}
            required
          />
          <small className="text-muted">
            This is what the office looks for on the statement, so copy it
            exactly as printed.
          </small>
        </div>
        <div className="col-md-6 form-group">
          <label>Photo or PDF of the slip</label>
          <input
            type="file"
            className="form-control-file"
            accept=".jpg,.jpeg,.png,.webp,.pdf"
            onChange={(e) => setImage(e.target.files[0] || null)}
            required
          />
          <small className="text-muted">
            Up to 5 MB. Make sure the amount, date and voucher number are
            readable — an unreadable slip is the usual reason one comes back.
          </small>
        </div>
      </div>

      <div className="form-group">
        <label>Anything the office should know (optional)</label>
        <textarea
          className="form-control"
          rows={2}
          value={fields.note}
          onChange={(e) => set("note", e.target.value)}
        />
      </div>

      <button className="btn btn-primary" disabled={submitting}>
        <i className="fas fa-upload me-1"></i>
        {submitting ? "Submitting…" : "Submit for verification"}
      </button>
    </form>
  );
}
