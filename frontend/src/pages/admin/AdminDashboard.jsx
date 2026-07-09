import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import ThemedChart, {
  CHART_COLORS,
  SOFT_PALETTE,
} from "../../components/ThemedChart";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** Stat card from the stats-grid in hod_template/home_content.html. */
function StatCard({ icon, tone, color, number, label, to }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${tone}`}>
        <i className={icon}></i>
      </div>
      <div className="stat-number" style={{ color: `var(--${color})` }}>
        {number}
      </div>
      <p className="stat-label">{label}</p>
      <Link to={to} className="btn btn-primary btn-sm mt-2">
        <i className="fas fa-eye"></i> View All
      </Link>
    </div>
  );
}

/** Card wrapper for each chart section (erpnext-card + header). */
function ChartCard({ icon, title, children }) {
  return (
    <div className="erpnext-card">
      <div className="card-header">
        <h3 className="card-title">
          <i className={`${icon} me-2`}></i>
          {title}
        </h3>
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}

const QUICK_ACTIONS = [
  { text: "Add Student", icon: "fas fa-user-plus", to: "/student/add/" },
  { text: "Add Staff", icon: "fas fa-user-tie", to: "/staff/add" },
  { text: "Add Course", icon: "fas fa-graduation-cap", to: "/course/add" },
  { text: "Add Subject", icon: "fas fa-book-open", to: "/subject/add/" },
];

/**
 * Admin dashboard, converted from hod_template/home_content.html +
 * hod_views.admin_home. Stats and chart series come from
 * /dashboard/admin/ with the exact field names of the old view context.
 */
function AdminDashboard() {
  usePageHeader({ title: "Dashboard", breadcrumb: [{ text: "Dashboard" }] });
  const { addMessage } = useMessages();

  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    dashboardAPI
      .adminHome()
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

  /* --- Chart configs, one per canvas in the template's custom_js --- */

  const staffStudentsPie = useCallback(
    () => ({
      type: "doughnut",
      data: {
        labels: ["Students", "Staff"],
        datasets: [
          {
            data: [stats.total_students, stats.total_staff],
            backgroundColor: [SOFT_PALETTE[0], SOFT_PALETTE[1]],
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
            labels: { padding: 20, usePointStyle: true },
          },
        },
      },
    }),
    [stats]
  );

  const barScales = (theme) => ({
    y: {
      beginAtZero: true,
      ticks: { color: theme.textColor, font: { weight: "600" } },
      grid: { color: theme.gridColor },
    },
    x: {
      ticks: { color: theme.textColor, font: { weight: "600" } },
      grid: { display: false },
    },
  });

  const attendancePerSubjectBar = useCallback(
    (theme) => ({
      type: "bar",
      data: {
        labels: stats.subject_list,
        datasets: [
          {
            label: "Attendance",
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
        scales: barScales(theme),
      },
    }),
    [stats]
  );

  const studentAttendanceBar = useCallback(
    (theme) => ({
      type: "bar",
      data: {
        labels: stats.student_name_list,
        datasets: [
          {
            label: "Present",
            data: stats.student_attendance_present_list,
            backgroundColor: CHART_COLORS.success,
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: "Absent/Leave",
            data: stats.student_attendance_leave_list,
            backgroundColor: CHART_COLORS.danger,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { padding: 20, usePointStyle: true },
          },
        },
        scales: barScales(theme),
      },
    }),
    [stats]
  );

  const studentsPerCoursePie = useCallback(
    () => ({
      type: "doughnut",
      data: {
        labels: stats.course_name_list,
        datasets: [
          {
            data: stats.student_count_list_in_course,
            backgroundColor: SOFT_PALETTE,
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
            labels: { padding: 15, usePointStyle: true },
          },
        },
      },
    }),
    [stats]
  );

  const studentsPerSubjectPie = useCallback(
    () => ({
      type: "doughnut",
      data: {
        labels: stats.subject_list,
        datasets: [
          {
            data: stats.student_count_list_in_subject,
            backgroundColor: [
              CHART_COLORS.danger,
              CHART_COLORS.success,
              CHART_COLORS.warning,
              CHART_COLORS.info,
              CHART_COLORS.primary,
              "#6f42c1",
              "#20c997",
              "#fd7e14",
              "#e83e8c",
            ],
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
            labels: { padding: 15, usePointStyle: true },
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
        <StatCard
          icon="fas fa-user-graduate"
          tone="primary"
          color="primary-color"
          number={stats?.total_students ?? 0}
          label="Total Students"
          to="/student/manage/"
        />
        <StatCard
          icon="fas fa-users"
          tone="success"
          color="success-color"
          number={stats?.total_staff ?? 0}
          label="Total Staff"
          to="/staff/manage/"
        />
        <StatCard
          icon="fas fa-graduation-cap"
          tone="warning"
          color="warning-color"
          number={stats?.total_course ?? 0}
          label="Total Courses"
          to="/course/manage/"
        />
        <StatCard
          icon="fas fa-book"
          tone="danger"
          color="danger-color"
          number={stats?.total_subject ?? 0}
          label="Total Subjects"
          to="/course/manage/"
        />
      </div>

      {/* Charts Section */}
      {stats && (
        <>
          <div className="row">
            <div className="col-lg-6">
              <ChartCard icon="fas fa-chart-pie" title="Staff & Students Overview">
                <ThemedChart makeConfig={staffStudentsPie} height={300} />
              </ChartCard>
            </div>
            <div className="col-lg-6">
              <ChartCard icon="fas fa-chart-bar" title="Attendance Per Subject">
                <ThemedChart makeConfig={attendancePerSubjectBar} height={300} />
              </ChartCard>
            </div>
          </div>

          {/* Student Attendance Overview */}
          <div className="row">
            <div className="col-12">
              <ChartCard
                icon="fas fa-calendar-check"
                title="Student Attendance & Leave Overview"
              >
                <ThemedChart makeConfig={studentAttendanceBar} height={400} />
              </ChartCard>
            </div>
          </div>

          {/* Course and Subject Distribution */}
          <div className="row">
            <div className="col-lg-6">
              <ChartCard icon="fas fa-chart-pie" title="Students Per Course">
                <ThemedChart makeConfig={studentsPerCoursePie} height={300} />
              </ChartCard>
            </div>
            <div className="col-lg-6">
              <ChartCard icon="fas fa-chart-doughnut" title="Students Per Subject">
                <ThemedChart makeConfig={studentsPerSubjectPie} height={300} />
              </ChartCard>
            </div>
          </div>
        </>
      )}

      {/* Quick Actions */}
      <div className="row">
        <div className="col-12">
          <ChartCard icon="fas fa-bolt" title="Quick Actions">
            <div className="row">
              {QUICK_ACTIONS.map((action) => (
                <div className="col-md-3 mb-3" key={action.text}>
                  <Link to={action.to} className="btn btn-primary w-100">
                    <i className={`${action.icon} mb-2`}></i>
                    <br />
                    {action.text}
                  </Link>
                </div>
              ))}
            </div>
          </ChartCard>
        </div>
      </div>
    </>
  );
}

export default AdminDashboard;
