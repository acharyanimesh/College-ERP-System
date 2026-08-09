import { useState } from "react";
import { Link } from "react-router-dom";
import { courseAPI } from "../../api/academics";
import feeAPI from "../../api/fees";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

const STATUS_BADGE = {
  paid: "badge-success",
  due: "badge-info",
  partial: "badge-warning",
  overdue: "badge-danger",
  cancelled: "badge-secondary",
};

/** Every bill the college has raised, filterable by class and state. */
function InvoiceRegister() {
  usePageHeader({
    title: "Fee Invoices",
    breadcrumb: [{ text: "Fee Invoices" }],
  });

  const [filters, setFilters] = useState({ course: "", status: "", q: "" });
  const [query, setQuery] = useState("");

  const { data: invoices } = useApi(
    () =>
      feeAPI.getInvoices({
        course: filters.course || undefined,
        status: filters.status || undefined,
        q: filters.q || undefined,
      }),
    [filters.course, filters.status, filters.q]
  );
  const { data: courses } = useApi(() => courseAPI.getAll());

  const setFilter = (name, value) =>
    setFilters((f) => ({ ...f, [name]: value }));

  return (
    <ListCard title="Fee Invoices" scrollBody>
      <div className="row">
        <div className="col-md-4 form-group">
          <select
            className="form-control"
            value={filters.course}
            onChange={(e) => setFilter("course", e.target.value)}
          >
            <option value="">All courses</option>
            {courses?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name_with_abbr}
              </option>
            ))}
          </select>
        </div>
        <div className="col-md-3 form-group">
          <select
            className="form-control"
            value={filters.status}
            onChange={(e) => setFilter("status", e.target.value)}
          >
            <option value="">All invoices</option>
            <option value="outstanding">Anything still owed</option>
            <option value="overdue">Overdue only</option>
          </select>
        </div>
        <div className="col-md-5 form-group">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setFilter("q", query);
            }}
          >
            <div className="input-group">
              <input
                className="form-control"
                placeholder="Search by invoice number, name or roll…"
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

      <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
        <thead className="thead-dark">
          <tr>
            <th>Invoice</th>
            <th>Student</th>
            <th>Class</th>
            <th>Due</th>
            <th>Payable</th>
            <th>Paid</th>
            <th>Balance</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {!invoices?.length && (
            <tr>
              <td colSpan={8} className="text-center">
                No invoices match. Raise some from{" "}
                <Link to="/accountant/fees/run/">Raise Fee Invoices</Link>.
              </td>
            </tr>
          )}
          {invoices?.map((inv) => (
            <tr key={inv.id}>
              <td>
                <Link to={`/accountant/fees/invoices/${inv.id}`}>
                  {inv.number}
                </Link>
              </td>
              <td>
                {inv.student_name}
                <br />
                <small className="text-muted">{inv.student_roll || "—"}</small>
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
              <td>{formatMoney(inv.payable)}</td>
              <td>{formatMoney(inv.paid)}</td>
              <td className="font-weight-bold">{formatMoney(inv.balance)}</td>
              <td>
                <span className={`badge ${STATUS_BADGE[inv.status] || "badge-info"}`}>
                  {inv.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {invoices?.length >= 300 && (
        <small className="text-muted">
          Showing the first 300 — narrow it down with the filters above.
        </small>
      )}
    </ListCard>
  );
}

export default InvoiceRegister;
