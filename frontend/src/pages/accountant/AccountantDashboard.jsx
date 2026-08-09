import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

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
 * Accounts office dashboard: what came in, what is still owed, who is behind.
 *
 * The billing, collection and reporting screens land in the phases after this
 * one; until a fee structure exists and an invoice run has been made, every
 * figure here is legitimately zero and the tables are legitimately empty.
 */
function AccountantDashboard() {
  usePageHeader({
    title: "Accounts Dashboard",
    breadcrumb: [{ text: "Accounts Dashboard" }],
  });
  const { data: stats } = useApi(() => dashboardAPI.accountantHome());

  const nothingBilledYet = stats && !stats.invoices_total;

  return (
    <>
      <div className="stats-grid">
        <StatCard
          icon="fas fa-cash-register"
          tone="success"
          value={formatMoney(stats?.collected_today)}
          label="Collected Today"
        />
        <StatCard
          icon="fas fa-calendar-alt"
          tone="primary"
          value={formatMoney(stats?.collected_this_month)}
          label="Collected This Month"
        />
        <StatCard
          icon="fas fa-file-invoice-dollar"
          tone="warning"
          value={formatMoney(stats?.outstanding_total)}
          label="Outstanding"
        />
        <StatCard
          icon="fas fa-exclamation-triangle"
          tone="danger"
          value={formatMoney(stats?.overdue_total)}
          label="Overdue"
        />
      </div>

      {/* Work the office owes an answer on, ahead of everything else on the
          page: a slip nobody looks at is a student who has paid and is still
          being chased for the money. */}
      {stats?.slips_pending > 0 && (
        <div className="row">
          <div className="col-12">
            <div className="alert alert-warning d-flex justify-content-between align-items-center">
              <span>
                <i className="fas fa-university me-2"></i>
                <strong>{stats.slips_pending}</strong> bank deposit
                {stats.slips_pending === 1 ? "" : "s"} waiting to be checked
                against the statement.
              </span>
              <Link className="btn btn-sm btn-primary" to="/accountant/fees/slips/">
                Open the queue
              </Link>
            </div>
          </div>
        </div>
      )}

      {nothingBilledYet && (
        <div className="row">
          <div className="col-12">
            <div className="erpnext-card">
              <div className="card-body">
                <h5 className="card-title">Nothing has been billed yet</h5>
                <p className="text-muted mb-0">
                  Once fee structures are set up and an invoice run has been
                  made, collections and arrears will appear here.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="row">
        <div className="col-lg-7">
          <div className="erpnext-card">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h3 className="card-title">
                <i className="fas fa-clock me-2"></i>
                Most Overdue
              </h3>
              <span className="badge badge-danger">
                {stats?.students_in_arrears ?? 0} student
                {stats?.students_in_arrears === 1 ? "" : "s"} in arrears
              </span>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Student</th>
                    <th>Invoice</th>
                    <th>Late</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.most_overdue?.length ? (
                    stats.most_overdue.map((inv) => (
                      <tr key={inv.id}>
                        <td>
                          {inv.student_name}
                          <br />
                          <small className="text-muted">
                            {inv.student_roll || "—"} · {inv.course} · Sem{" "}
                            {inv.semester}
                          </small>
                        </td>
                        <td>{inv.number}</td>
                        <td>
                          <span className="badge badge-danger">
                            {inv.days_overdue}d
                          </span>
                        </td>
                        <td>{formatMoney(inv.balance)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="text-center">
                        Nothing overdue.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-hourglass-half me-2"></i>
                Falling Due This Week
              </h3>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Student</th>
                    <th>Due</th>
                    <th>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.due_this_week?.length ? (
                    stats.due_this_week.map((inv) => (
                      <tr key={inv.id}>
                        <td>{inv.student_name}</td>
                        <td>{inv.due_date}</td>
                        <td>{formatMoney(inv.balance)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="text-center">
                        Nothing falls due in the next seven days.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-lg-5">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-wallet me-2"></i>
                Collection By Mode
              </h3>
            </div>
            <div className="card-body">
              {stats?.collection_by_mode?.length ? (
                <table className="table table-bordered">
                  <thead className="thead-dark">
                    <tr>
                      <th>Mode</th>
                      <th>Receipts</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.collection_by_mode.map((m) => (
                      <tr key={m.mode}>
                        <td>{m.mode_display || m.mode}</td>
                        <td>{m.count}</td>
                        <td>{formatMoney(m.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted mb-0">Nothing collected yet.</p>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-7">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-receipt me-2"></i>
                Recent Receipts
              </h3>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Receipt</th>
                    <th>Student</th>
                    <th>Mode</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.recent_payments?.length ? (
                    stats.recent_payments.map((p) => (
                      <tr key={p.receipt_no}>
                        <td>
                          {p.receipt_no}
                          <br />
                          <small className="text-muted">{p.received_on}</small>
                        </td>
                        <td>{p.student_name}</td>
                        <td>{p.mode_display}</td>
                        <td>{formatMoney(p.amount)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="text-center">
                        No receipts yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default AccountantDashboard;
