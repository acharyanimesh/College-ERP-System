import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import useApi from "../../hooks/useApi";
import { rs } from "../../constants/money";
import { usePageHeader } from "../../layouts/Layout";

const QUICK_ACTIONS = [
  { text: "Collect Fee", icon: "fas fa-cash-register", to: "/accountant/collect/", btn: "btn-primary" },
  { text: "Payments", icon: "fas fa-receipt", to: "/accountant/payments/", btn: "btn-success" },
  { text: "Fee Structure", icon: "fas fa-list-ol", to: "/accountant/fees/", btn: "btn-warning" },
  { text: "Library Fines", icon: "fas fa-book", to: "/accountant/library-fines/", btn: "btn-secondary" },
];

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

/** Accountant dashboard: what the term should bring in, what has, what is owed. */
function AccountantDashboard() {
  usePageHeader({
    title: "Accountant Dashboard",
    breadcrumb: [{ text: "Accountant Dashboard" }],
  });
  const { data: stats } = useApi(() => dashboardAPI.accountantHome());
  const s = stats || {};

  return (
    <>
      <div className="stats-grid">
        <StatCard icon="fas fa-exclamation-triangle" tone="danger" value={rs(s.term_outstanding)} label="Outstanding This Term" />
        <StatCard icon="fas fa-hand-holding-usd" tone="success" value={rs(s.term_collected)} label="Collected This Term" />
        <StatCard icon="fas fa-percentage" tone="primary" value={`${s.collection_rate ?? 0}%`} label="Collection Rate" />
        <StatCard icon="fas fa-user-graduate" tone="warning" value={s.total_students ?? 0} label="Active Students" />
      </div>

      <div className="row">
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-bolt me-2"></i>
                Quick Actions
              </h3>
            </div>
            <div className="card-body">
              <div className="row">
                {QUICK_ACTIONS.map((action) => (
                  <div className="col-md-3 mb-3" key={action.text}>
                    <Link to={action.to} className={`btn ${action.btn} btn-sm mt-2 w-100`}>
                      <i className={`${action.icon} mb-2`}></i>
                      <br />
                      {action.text}
                    </Link>
                  </div>
                ))}
              </div>
              <hr />
              <p className="text-muted mb-0">
                Collected all-time: <strong>{rs(s.collected_all_time)}</strong>
                {" · "}Today: <strong>{rs(s.collected_today)}</strong>
                {" · "}
                {s.status_counts?.paid ?? 0} paid up · {s.status_counts?.partial ?? 0} part-paid ·{" "}
                {s.status_counts?.unpaid ?? 0} unpaid
                {s.status_counts?.unbilled ? ` · ${s.status_counts.unbilled} unbilled` : ""}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-lg-7">
          <div className="erpnext-card">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h3 className="card-title">
                <i className="fas fa-receipt me-2"></i>
                Recent Receipts
              </h3>
              <Link to="/accountant/payments/" className="btn btn-sm btn-outline-primary">
                All receipts
              </Link>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Receipt</th>
                    <th>Student</th>
                    <th>Sem</th>
                    <th>Amount</th>
                    <th>When</th>
                  </tr>
                </thead>
                <tbody>
                  {s.recent_payments?.length ? (
                    s.recent_payments.map((p) => (
                      <tr key={p.id}>
                        <td>{p.receipt_no}</td>
                        <td>
                          {p.student_name}
                          <br />
                          <small className="text-muted">
                            {p.student_roll || "—"} · {p.student_course}
                          </small>
                        </td>
                        <td>{p.semester}</td>
                        <td>{rs(p.amount)}</td>
                        <td>{p.collected_on}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="text-center">
                        No payments recorded yet.
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
                <i className="fas fa-layer-group me-2"></i>
                By Course (this term)
              </h3>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Course</th>
                    <th>Collected</th>
                    <th>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {s.by_course?.length ? (
                    s.by_course.map((c) => (
                      <tr key={c.course}>
                        <td>
                          {c.course}
                          <br />
                          <small className="text-muted">{c.students} students</small>
                        </td>
                        <td>{rs(c.collected)}</td>
                        <td>
                          {c.outstanding ? (
                            <span className="badge badge-danger">{rs(c.outstanding)}</span>
                          ) : (
                            <span className="badge badge-success">Clear</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="text-center">
                        No students on the roll yet.
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
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h3 className="card-title">
                <i className="fas fa-book me-2"></i>
                Library Fines
              </h3>
              <Link to="/accountant/library-fines/" className="btn btn-sm btn-outline-secondary">
                View
              </Link>
            </div>
            <div className="card-body">
              <p className="text-muted mb-0">
                Collected at the library desk: <strong>{rs(s.library_fines_collected)}</strong>
                {" · "}Still owed on overdue loans:{" "}
                <strong className={s.library_fines_outstanding ? "text-danger" : ""}>
                  {rs(s.library_fines_outstanding)}
                </strong>
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default AccountantDashboard;
