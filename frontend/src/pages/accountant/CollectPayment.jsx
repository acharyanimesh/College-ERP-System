import { useState } from "react";
import { Link } from "react-router-dom";
import feeAPI from "../../api/fees";
import PaymentForm from "../../components/PaymentForm";
import Receipt from "../../components/Receipt";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * The counter, in the order the desk actually works: find the student, look
 * at what they owe, take the money, hand over the receipt.
 *
 * The search runs on demand rather than on every keystroke — the person at
 * the window says their roll number once, and a search-as-you-type box would
 * hammer the server for every prefix of it.
 */
function CollectPayment() {
  usePageHeader({
    title: "Collect Payment",
    breadcrumb: [{ text: "Collect Payment" }],
  });
  const { addMessage } = useMessages();

  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [receipt, setReceipt] = useState(null);

  const search = async (e) => {
    e.preventDefault();
    setSearching(true);
    setSelected(null);
    setReceipt(null);
    try {
      setResults(await feeAPI.collectable({ q: query || undefined }));
    } catch {
      addMessage("Could not search the outstanding bills.", "danger");
    } finally {
      setSearching(false);
    }
  };

  const collect = async (fields) => {
    setSubmitting(true);
    try {
      const result = await feeAPI.collect(selected.id, fields);
      setReceipt(result.payment);
      addMessage(
        `Receipt ${result.payment.receipt_no} — ${formatMoney(
          result.payment.amount
        )} received.`,
        "success"
      );
      // Reflect the new balance, and drop the bill off the list once settled.
      const updated = result.invoice;
      setSelected(Number(updated.balance) > 0 ? updated : null);
      setResults((rs) =>
        (rs || [])
          .map((r) => (r.id === updated.id ? { ...r, ...updated } : r))
          .filter((r) => Number(r.balance) > 0)
      );
    } catch (err) {
      const data = err.response?.data || {};
      addMessage(
        data.detail ||
          data.amount?.[0] ||
          data.reference?.[0] ||
          data.mode?.[0] ||
          data.received_on?.[0] ||
          "Could not record the payment.",
        "danger"
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <ListCard title="Find the bill">
        <form onSubmit={search}>
          <div className="row">
            <div className="col-md-8 form-group">
              <div className="input-group">
                <input
                  className="form-control"
                  placeholder="Roll number, name or invoice number…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  autoFocus
                />
                <button className="btn btn-primary" disabled={searching}>
                  <i className="fas fa-search me-1"></i>
                  {searching ? "Searching…" : "Search"}
                </button>
              </div>
              <small className="text-muted">
                Only bills with money still on them appear here. Leave it blank
                to list everything outstanding.
              </small>
            </div>
          </div>
        </form>

        {results && (
          <table className="table table-bordered table-hover mt-2">
            <thead className="thead-dark">
              <tr>
                <th>Invoice</th>
                <th>Student</th>
                <th>Class</th>
                <th>Due</th>
                <th>Balance</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {!results.length && (
                <tr>
                  <td colSpan={6} className="text-center">
                    Nothing outstanding matches that.
                  </td>
                </tr>
              )}
              {results.map((inv) => (
                <tr
                  key={inv.id}
                  className={selected?.id === inv.id ? "table-active" : ""}
                >
                  <td>
                    <Link to={`/accountant/fees/invoices/${inv.id}`}>
                      {inv.number}
                    </Link>
                  </td>
                  <td>
                    {inv.student_name}
                    <br />
                    <small className="text-muted">
                      {inv.student_roll || "—"}
                    </small>
                  </td>
                  <td>
                    {inv.course_name} · Sem {inv.semester}
                  </td>
                  <td>
                    {inv.due_date}
                    {inv.days_overdue > 0 && (
                      <>
                        <br />
                        <small className="text-danger">
                          {inv.days_overdue} days late
                        </small>
                      </>
                    )}
                  </td>
                  <td className="font-weight-bold">
                    {formatMoney(inv.balance)}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm btn-success"
                      onClick={() => {
                        setSelected(inv);
                        setReceipt(null);
                      }}
                    >
                      Take payment
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </ListCard>

      {selected && (
        <ListCard
          title={`Take payment — ${selected.student_name} · ${selected.number}`}
        >
          <PaymentForm
            key={`${selected.id}-${selected.balance}`}
            invoice={selected}
            onSubmit={collect}
            submitting={submitting}
          />
        </ListCard>
      )}

      {receipt && (
        <ListCard title="Receipt">
          <Receipt payment={receipt} onPrint={() => window.print()} />
        </ListCard>
      )}
    </>
  );
}

export default CollectPayment;
