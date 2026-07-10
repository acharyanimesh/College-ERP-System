import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import ThemedChart, { CHART_COLORS } from "../../components/ThemedChart";
import { usePageHeader, useMessages } from "../../layouts/Layout";

const QUICK_ACTIONS = [
  {
    text: "Take Attendance",
    icon: "fas fa-check-circle",
    to: "/staff/attendance/take/",
    btn: "btn-primary",
  },
  {
    text: "Add Result",
    icon: "fas fa-plus-circle",
    to: "/staff/result/add/",
    btn: "btn-success",
  },
  {
    text: "Apply for Leave",
    icon: "fas fa-calendar-plus",
    to: "/staff/apply/leave/",
    btn: "btn-warning",
  },
  {
    text: "Add Books",
    icon: "fas fa-book-open",
    to: "/staff/addbook/",
    btn: "btn-secondary",
  },
];

/**
 * Staff dashboard, converted from staff_template/erpnext_staff_home.html +
 * staff_views.staff_home. (The template's Firebase push-notification setup
 * is intentionally not carried over; notifications are handled separately.)
 */
function StaffDashboard() {
  usePageHeader({
    title: "Staff Dashboard",
    breadcrumb: [{ text: "Staff Dashboard" }],
  });
  const { addMessage } = useMessages();

  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    dashboardAPI
      .staffHome()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        if (!cancelled) addMessage("Could not load dashboard data.", "danger");
      });
    return () => {
      cancelled = true;
    };
  }, [addMessage]);

  const attendanceLeavePie = useCallback(
    (theme) => ({
      type: "doughnut",
      data: {
        labels: ["Attendance", "Leave"],
        datasets: [
          {
            data: [stats.total_attendance, stats.total_leave],
            backgroundColor: [CHART_COLORS.success, CHART_COLORS.warning],
            borderWidth: 0,
            cutout: "60%",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              padding: 20,
              usePointStyle: true,
              color: theme.textColor,
              font: { size: 14, weight: "600" },
            },
          },
        },
      },
    }),
    [stats]
  );

  const subjectAttendanceBar = useCallback(
    (theme) => ({
      type: "bar",
      data: {
        labels: stats.subject_list,
        datasets: [
          {
            label: "Attendance Count",
            data: stats.attendance_list,
            backgroundColor: CHART_COLORS.info,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: theme.gridColor },
            ticks: { color: theme.textColor, font: { weight: "600" } },
          },
          x: {
            grid: { display: false },
            ticks: { color: theme.textColor, font: { weight: "600" } },
          },
        },
      },
    }),
    [stats]
  );

  return (
    <>
      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon primary">
            <i className="fas fa-user-graduate"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--primary-color)" }}>
              {stats?.total_students ?? 0}
            </div>
            <p className="stat-label">Total Students</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon success">
            <i className="fas fa-calendar-check"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--success-color)" }}>
              {stats?.total_attendance ?? 0}
            </div>
            <p className="stat-label">Total Attendance Taken</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon warning">
            <i className="fas fa-calendar-times"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--warning-color)" }}>
              {stats?.total_leave ?? 0}
            </div>
            <p className="stat-label">Total Leave Applied</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon danger">
            <i className="fas fa-book"></i>
          </div>
          <div className="stat-card-body">
            <div className="stat-number" style={{ color: "var(--danger-color)" }}>
              {stats?.total_subject ?? 0}
            </div>
            <p className="stat-label">Total Subjects</p>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      {stats && (
        <div className="row">
          <div className="col-lg-6">
            <div className="erpnext-card">
              <div className="card-header">
                <h3 className="card-title">
                  <i className="fas fa-chart-pie me-2"></i>
                  Attendance vs Leave Overview
                </h3>
              </div>
              <div className="card-body">
                <ThemedChart makeConfig={attendanceLeavePie} height={300} />
              </div>
            </div>
          </div>
          <div className="col-lg-6">
            <div className="erpnext-card">
              <div className="card-header">
                <h3 className="card-title">
                  <i className="fas fa-chart-bar me-2"></i>
                  Subject-wise Attendance
                </h3>
              </div>
              <div className="card-body">
                <ThemedChart makeConfig={subjectAttendanceBar} height={300} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
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
                    <Link
                      to={action.to}
                      className={`btn ${action.btn} btn-sm mt-2 w-100`}
                    >
                      <i className={`${action.icon} mb-2`}></i>
                      <br />
                      {action.text}
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Assigned Subjects */}
      <div className="row">
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-book me-2"></i>
                My Assigned Subjects
              </h3>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>#</th>
                    <th>Subject</th>
                    <th>Course(s)</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.assigned_subjects?.length ? (
                    stats.assigned_subjects.map((subject, i) => (
                      <tr key={subject.id ?? i}>
                        <td>{i + 1}</td>
                        <td>{subject.name}</td>
                        <td>
                          {subject.courses?.length ? (
                            subject.courses.map((c, j) => (
                              <span key={c.short_name}>
                                <span title={c.name}>{c.short_name}</span>
                                {j < subject.courses.length - 1 && ", "}
                              </span>
                            ))
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="text-center">
                        No subjects assigned to you yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activities */}
      <div className="row">
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header">
              <h3 className="card-title">
                <i className="fas fa-clock me-2"></i>
                Recent Activities
              </h3>
            </div>
            <div className="card-body">
              <div className="row">
                <div className="col-md-4">
                  <div className="d-flex align-items-center mb-3">
                    <div className="stat-icon success me-3">
                      <i className="fas fa-calendar-check"></i>
                    </div>
                    <div>
                      <h6 className="mb-0">Attendance Records</h6>
                      <small className="text-muted">
                        {stats?.total_attendance ?? 0} records taken
                      </small>
                    </div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="d-flex align-items-center mb-3">
                    <div className="stat-icon warning me-3">
                      <i className="fas fa-users"></i>
                    </div>
                    <div>
                      <h6 className="mb-0">Students Managed</h6>
                      <small className="text-muted">
                        {stats?.total_students ?? 0} students in classes
                      </small>
                    </div>
                  </div>
                </div>
                <div className="col-md-4">
                  <div className="d-flex align-items-center mb-3">
                    <div className="stat-icon primary me-3">
                      <i className="fas fa-book"></i>
                    </div>
                    <div>
                      <h6 className="mb-0">Subjects Teaching</h6>
                      <small className="text-muted">
                        {stats?.total_subject ?? 0} subjects assigned
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default StaffDashboard;
