import { useState } from "react";
import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import libraryAPI from "../../api/library";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const QUICK_ACTIONS = [
  { text: "Borrow Requests", icon: "fas fa-inbox", to: "/librarian/requests/", btn: "btn-primary" },
  { text: "Issued Books", icon: "fas fa-hand-holding", to: "/librarian/issued/", btn: "btn-success" },
  { text: "Fines", icon: "fas fa-money-bill-wave", to: "/librarian/fines/", btn: "btn-danger" },
  { text: "Add Book", icon: "fas fa-book-medical", to: "/librarian/books/add/", btn: "btn-warning" },
  { text: "Manage Books", icon: "fas fa-book-open", to: "/librarian/books/", btn: "btn-secondary" },
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

/** Librarian dashboard: what needs deciding, what is out, what is late. */
function LibrarianDashboard() {
  usePageHeader({
    title: "Librarian Dashboard",
    breadcrumb: [{ text: "Librarian Dashboard" }],
  });
  const { addMessage } = useMessages();
  const { data: stats } = useApi(() => dashboardAPI.librarianHome());
  const [sending, setSending] = useState(false);

  /**
   * Fires the same sweep as the `send_due_reminders` management command, so
   * the desk isn't dependent on the scheduled job having been set up. Safe to
   * press twice — each loan is only ever reminded about once.
   */
  const sendReminders = async () => {
    setSending(true);
    try {
      const result = await libraryAPI.sendReminders();
      addMessage(
        result.sent
          ? `${result.sent} due-date reminder${result.sent === 1 ? "" : "s"} sent.`
          : "No books are due in 3 days that haven't already been reminded about.",
        result.sent ? "success" : "info"
      );
    } catch {
      addMessage("Could not send the reminders.", "danger");
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div className="stats-grid">
        <StatCard icon="fas fa-inbox" tone="warning" value={stats?.pending_requests ?? 0} label="Requests Awaiting Decision" />
        <StatCard icon="fas fa-book-reader" tone="primary" value={stats?.books_on_loan ?? 0} label="Books On Loan" />
        <StatCard icon="fas fa-exclamation-triangle" tone="danger" value={stats?.overdue_count ?? 0} label="Overdue" />
        <StatCard icon="fas fa-book" tone="success" value={stats?.total_titles ?? 0} label="Titles In Catalogue" />
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
              <button
                type="button"
                className="btn btn-outline-primary btn-sm"
                onClick={sendReminders}
                disabled={sending}
              >
                <i className="fas fa-paper-plane me-2"></i>
                {sending ? "Sending…" : "Send due-date reminders now"}
              </button>
              {/* Deliberately says nothing about the scheduled job behind
                  this: whether it is set up is not something the librarian
                  can see or change, and naming a shell command on a desk
                  screen only raises questions. See the send_due_reminders
                  management command for the scheduling side. */}
              <small className="d-block text-muted mt-2">
                Reminds every student with a book due in 3 days. Safe to press
                any time — nobody is reminded twice.
              </small>
            </div>
          </div>
        </div>
      </div>

      <div className="row">
        <div className="col-lg-7">
          <div className="erpnext-card">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h3 className="card-title">
                <i className="fas fa-inbox me-2"></i>
                Requests Waiting On You
              </h3>
              <Link to="/librarian/requests/" className="btn btn-sm btn-outline-primary">
                Open queue
              </Link>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Student</th>
                    <th>Book</th>
                    <th>Requested</th>
                    <th>Stock</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.recent_requests?.length ? (
                    stats.recent_requests.map((req) => (
                      <tr key={req.id}>
                        <td>
                          {req.student_name}
                          <br />
                          <small className="text-muted">
                            {req.student_roll || "—"} · {req.student_course}
                          </small>
                        </td>
                        <td>{req.book_name}</td>
                        <td>{req.requested_at}</td>
                        <td>
                          <span
                            className={`badge ${
                              req.available_copies ? "badge-success" : "badge-secondary"
                            }`}
                          >
                            {req.available_copies} free
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="text-center">
                        Nothing waiting — the queue is clear.
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
            <div className="card-header d-flex justify-content-between align-items-center">
              <h3 className="card-title">
                <i className="fas fa-clock me-2"></i>
                Most Overdue
              </h3>
              <span className="badge badge-danger">
                Rs. {stats?.fines_outstanding ?? 0} due
              </span>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>Student</th>
                    <th>Book</th>
                    <th>Late</th>
                    <th>Fine</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.overdue_loans?.length ? (
                    stats.overdue_loans.map((loan) => (
                      <tr key={loan.id}>
                        <td>{loan.student_name}</td>
                        <td>{loan.book_name}</td>
                        <td>
                          <span className="badge badge-danger">
                            {loan.days_overdue}d
                          </span>
                        </td>
                        <td>Rs. {loan.fine}</td>
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
      </div>

      <div className="row">
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-layer-group me-2"></i>
                Catalogue
              </h3>
            </div>
            <div className="card-body">
              <p className="text-muted">
                {stats?.total_copies ?? 0} copies across {stats?.total_titles ?? 0}{" "}
                titles · {stats?.copies_out ?? 0} currently out ·{" "}
                {stats?.awaiting_pickup ?? 0} approved and awaiting pickup.
              </p>
              {stats?.category_breakdown?.map((c) => (
                <span key={c.label} className="badge badge-info mr-2 mb-2">
                  {c.label}: {c.count}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default LibrarianDashboard;
