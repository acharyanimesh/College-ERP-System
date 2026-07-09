import { useCallback, useEffect, useState } from "react";
import dashboardAPI from "../../api/dashboard";
import ThemedChart, { CHART_COLORS } from "../../components/ThemedChart";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Student dashboard, converted from
 * student_template/erpnext_student_home.html + student_views.student_home.
 * (Firebase push-notification setup intentionally not carried over.)
 */
function StudentDashboard() {
  usePageHeader({ title: "Student Homepage" });
  const { addMessage } = useMessages();

  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;
    dashboardAPI
      .studentHome()
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

  const attendanceDonut = useCallback(
    (theme) => ({
      type: "doughnut",
      data: {
        labels: ["Present", "Absent"],
        datasets: [
          {
            data: [stats.percent_present, stats.percent_absent],
            backgroundColor: [CHART_COLORS.success, CHART_COLORS.danger],
            borderColor: [CHART_COLORS.success, CHART_COLORS.danger],
            borderWidth: 2,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: {
              usePointStyle: true,
              padding: 20,
              color: theme.textColor,
              font: { size: 12 },
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
        labels: stats.data_name,
        datasets: [
          {
            label: "Present In Class",
            backgroundColor: CHART_COLORS.success,
            borderColor: CHART_COLORS.success,
            data: stats.data_present,
          },
          {
            label: "Absent In Class",
            backgroundColor: CHART_COLORS.danger,
            borderColor: CHART_COLORS.danger,
            data: stats.data_absent,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: theme.textColor } },
        },
        scales: {
          y: {
            ticks: { color: theme.textColor },
            grid: { color: theme.gridColor },
          },
          x: {
            ticks: { color: theme.textColor },
            grid: { color: theme.gridColor },
          },
        },
      },
    }),
    [stats]
  );

  return (
    <div className="page-container">
      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon bg-blue">
            <i className="fas fa-calendar-alt"></i>
          </div>
          <div className="stat-content">
            <div className="stat-number">{stats?.total_attendance ?? 0}</div>
            <div className="stat-label">Total Attendance</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-green">
            <i className="fas fa-calendar-check"></i>
          </div>
          <div className="stat-content">
            <div className="stat-number">
              {stats?.percent_present ?? 0}
              <span className="stat-unit">%</span>
            </div>
            <div className="stat-label">Percentage Present</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-red">
            <i className="fas fa-calendar-minus"></i>
          </div>
          <div className="stat-content">
            <div className="stat-number">
              {stats?.percent_absent ?? 0}
              <span className="stat-unit">%</span>
            </div>
            <div className="stat-label">Percentage Absent</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-purple">
            <i className="fas fa-book"></i>
          </div>
          <div className="stat-content">
            <div className="stat-number">{stats?.total_subject ?? 0}</div>
            <div className="stat-label">Total Subjects</div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      {stats && (
        <div className="row mt-4">
          <div className="col-lg-6">
            <div className="erpnext-card">
              <div className="card-header">
                <h5 className="card-title">Attendance Overview</h5>
              </div>
              <div className="card-body">
                <ThemedChart makeConfig={attendanceDonut} height={300} />
              </div>
            </div>
          </div>
          <div className="col-lg-6">
            <div className="erpnext-card">
              <div className="card-header">
                <h5 className="card-title">Subject-wise Attendance</h5>
              </div>
              <div className="card-body">
                <ThemedChart makeConfig={subjectAttendanceBar} height={300} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* My Subjects */}
      <div className="row mt-4">
        <div className="col-12">
          <div className="erpnext-card">
            <div className="card-header">
              <h5 className="card-title">
                <i className="fas fa-book me-2"></i>My Subjects
              </h5>
            </div>
            <div className="card-body">
              <table className="table table-bordered table-hover">
                <thead className="thead-dark">
                  <tr>
                    <th>#</th>
                    <th>Subject</th>
                    <th>Teacher</th>
                  </tr>
                </thead>
                <tbody>
                  {stats?.course_subjects?.length ? (
                    stats.course_subjects.map((cs, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        <td>{cs.subject_name}</td>
                        <td>
                          {cs.teacher_name || (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="text-center">
                        No subjects available for your course yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StudentDashboard;
