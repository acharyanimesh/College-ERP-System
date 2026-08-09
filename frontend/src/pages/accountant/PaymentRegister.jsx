import { useState } from "react";
import { Link } from "react-router-dom";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

const MODE_BADGE = {
  cash: "badge-success",
  cheque: "badge-info",
  bank: "badge-primary",
  online: "badge-secondary",
};

/**
 * The fee cash book: every receipt the college has issued, whoever took it.
 *
 * Nothing here is clickable through to an edit screen, and that is the point —
 * a FeePayment is append-only, so a mistake is corrected by an offsetting
 * adjustment on the bill, never by revising the receipt. The admin reads this
 * page too; the API is what keeps that read-only.
 *
 * The total comes from the server rather than being summed here, so the figure
 * the desk reconciles against is the same Decimal arithmetic that wrote the
 * receipts.
 */
function PaymentRegister() {
  usePageHeader({
    title: "Fee Collections",
    breadcrumb: [{ text: "Collections" }],
  });

  const [filters, setFilters] = useState({ mode: "", on: "", q: "" });
  const [query, setQuery] = useState("");

  const { data, loading } = useApi(
    () =>
      feeAPI.getPayments({
        mode: filters.mode || undefined,
        on: filters.on || undefined,
        q: filters.q || undefined,
      }),
    [filters.mode, filters.on, filters.q]
  );

  const setFilter = (name, value) =>
    setFilters((f) => ({ ...f, [name]: value }));

  const payments = data?.payments;

  return (
    <ListCard title="Fee Collections" scrollBody>
      <div className="row">
        <div className="col-md-3 form-group">
          <select
            className="form-control"
            value={filters.mode}
            onChange={(e) => setFilter("mode", e.target.value)}
          >
            <option value="">Every mode</option>
            <option value="cash">Cash at counter</option>
            <option value="cheque">Cheque</option>
            <option value="bank">Bank deposit</option>
            <option value="online">Online payment</option>
          </select>
        </div>
        <div className="col-md-3 form-group">
          <input
            type="date"
            className="form-control"
            value={filters.on}
            onChange={(e) => setFilter("on", e.target.value)}
            title="Receipts received on this date"
          />
        </div>
        <div className="col-md-6 form-group">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFilter("q", query);
            }}
          >
            <div className="input-group">
              <input
                className="form-control"
                placeholder="Receipt number, cheque or slip reference, invoice, name or roll…"
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

      <div className="alert alert-info">
        <i className="fas fa-lock"></i> {formatMoney(data?.total)} across{" "}
        {payments?.length ?? 0} receipt{payments?.length === 1 ? "" : "s"}
        {filters.on || filters.mode || filters.q ? " matching this filter" : ""}
        . These rows are the record of money actually received — they can't be
        edited or deleted, here or in the Django admin. A mistake is corrected
        by an adjustment on the bill, not by changing the receipt.
      </div>

      <table className="table table-bordered" style={{ minWidth: 1000 }}>
        <thead className="thead-dark">
          <tr>
            <th>Receipt No.</th>
            <th>Received</th>
            <th>Student</th>
            <th>Invoice</th>
            <th>Mode</th>
            <th>Amount</th>
            <th>Taken By</th>
          </tr>
        </thead>
        <tbody>
          {!loading && !payments?.length && (
            <tr>
              <td colSpan={7} className="text-center">
                No receipts match. Money is taken from{" "}
                <Link to="/accountant/fees/collect/">Collect Payment</Link>.
              </td>
            </tr>
          )}
          {payments?.map((p) => (
            <tr key={p.id}>
              <td>
                <code>{p.receipt_no}</code>
              </td>
              <td>{p.received_on}</td>
              <td>
                {p.student_name}
                <br />
                <small className="text-muted">{p.student_roll || "—"}</small>
              </td>
              <td>
                <Link to={`/accountant/fees/invoices/${p.invoice_id}`}>
                  {p.invoice_number}
                </Link>
              </td>
              <td>
                <span className={`badge ${MODE_BADGE[p.mode] || "badge-info"}`}>
                  {p.mode_display}
                </span>
                {p.reference && (
                  <>
                    <br />
                    <small className="text-muted">{p.reference}</small>
                  </>
                )}
              </td>
              <td className="font-weight-bold">{formatMoney(p.amount)}</td>
              <td>
                {p.collected_by_name || (
                  // Nobody took an online payment — the gateway confirmed it.
                  <span className="text-muted">Online</span>
                )}
                {p.note && (
                  <>
                    <br />
                    <small className="text-muted">{p.note}</small>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {payments?.length >= 300 && (
        <small className="text-muted">
          Showing the first 300 — narrow it down with the filters above.
        </small>
      )}
    </ListCard>
  );
}

export default PaymentRegister;
