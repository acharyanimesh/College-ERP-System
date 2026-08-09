import { Link } from "react-router-dom";
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

const STATUS_TEXT = {
  paid: "Paid",
  due: "Due",
  partial: "Part paid",
  overdue: "Overdue",
  cancelled: "Cancelled",
};

function StatCard({ icon, tone, value, label }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}>
        <i className={icon}></i>
      </div>
      <div className="stat-card-body">
        <div className="stat-number" style={{ color: `var(--${tone}-color)` }}>
          {value}
        </div>
        <p className="stat-label">{label}</p>
      </div>
    </div>
  );
}

/**
 * The student's own fee position.
 *
 * Cancelled bills stay in the list rather than disappearing — a student who
 * was told they owed something deserves to see that it was withdrawn.
 */
function MyFees() {
  usePageHeader({ title: "My Fees", breadcrumb: [{ text: "My Fees" }] });
  const { data: fees } = useApi(() => feeAPI.mine());

  if (!fees) return null;

  const owing = Number(fees.outstanding_total) > 0;
  const overdue = Number(fees.overdue_total) > 0;

  return (
    <>
      <div className="stats-grid">
        <StatCard
          icon="fas fa-wallet"
          tone={owing ? "warning" : "success"}
          value={formatMoney(fees.outstanding_total)}
          label="Outstanding"
        />
        <StatCard
          icon="fas fa-exclamation-triangle"
          tone="danger"
          value={formatMoney(fees.overdue_total)}
          label="Overdue"
        />
        <StatCard
          icon="fas fa-calendar-day"
          tone="primary"
          value={fees.next_due_date || "—"}
          label="Next Due Date"
        />
        <StatCard
          icon="fas fa-receipt"
          tone="success"
          value={formatMoney(fees.paid_total)}
          label="Paid So Far"
        />
      </div>

      {overdue && (
        <div className="row">
          <div className="col-12">
            <div className="alert alert-danger">
              <strong>
                {formatMoney(fees.overdue_total)} is past its due date
              </strong>{" "}
              across {fees.overdue_count} bill
              {fees.overdue_count === 1 ? "" : "s"}. Please settle it with the
              accounts office.
            </div>
          </div>
        </div>
      )}

      <ListCard
        title="My Bills"
        scrollBody
        action={
          <Link className="btn btn-secondary btn-sm" to="/student/receipts/">
            <i className="fas fa-receipt me-1"></i> My Receipts
          </Link>
        }
      >
        <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
          <thead className="thead-dark">
            <tr>
              <th>Invoice</th>
              <th>Semester</th>
              <th>Issued</th>
              <th>Due</th>
              <th>Payable</th>
              <th>Paid</th>
              <th>Balance</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {!fees.invoices.length && (
              <tr>
                <td colSpan={8} className="text-center">
                  Nothing has been billed to you yet.
                </td>
              </tr>
            )}
            {fees.invoices.map((inv) => (
              <tr key={inv.id}>
                <td>
                  <Link to={`/student/fees/${inv.id}`}>{inv.number}</Link>
                </td>
                <td>
                  {inv.course_name} · Sem {inv.semester}
                </td>
                <td>{inv.issued_date}</td>
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
                  <span
                    className={`badge ${STATUS_BADGE[inv.status] || "badge-info"}`}
                  >
                    {STATUS_TEXT[inv.status] || inv.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ListCard>
    </>
  );
}

export default MyFees;
