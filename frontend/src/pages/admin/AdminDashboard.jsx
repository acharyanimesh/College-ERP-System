import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import dashboardAPI from "../../api/dashboard";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** Stat tile — `tone` picks the accent bar/icon color (see erpnext-style.css). */
function StatCard({ icon, tone, number, label, to }) {
  return (
    <div className="stat-card" data-tone={tone}>
      {to && (
        <Link to={to} className="stat-card-link" title={`View ${label}`}>
          <i className="fas fa-arrow-right"></i>
        </Link>
      )}
      <div className={`stat-icon ${tone}`}>
        <i className={icon}></i>
      </div>
      <div className="stat-card-body">
        <div className="stat-number">{number}</div>
        <p className="stat-label">{label}</p>
      </div>
    </div>
  );
}

/** erpnext-card + header wrapper shared by every section below. */
function SectionCard({ icon, title, children, bodyStyle }) {
  return (
    <div className="erpnext-card">
      <div className="card-header">
        <h3 className="card-title dashboard-section-title">
          <i className={`${icon} me-2`}></i>
          {title}
        </h3>
      </div>
      <div className="card-body" style={bodyStyle}>
        {children}
      </div>
    </div>
  );
}

function AttentionGrid({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="attention-empty">
        <i className="fas fa-check-circle"></i>
        All clear — nothing needs your attention right now.
      </div>
    );
  }
  return (
    <div className="attention-grid">
      {alerts.map((alert, i) => {
        const className = `attention-item attention-item--${alert.severity}`;
        const inner = (
          <>
            <span className="attention-item-icon">
              <i className={alert.icon}></i>
            </span>
            <span className="attention-item-text">{alert.message}</span>
          </>
        );
        return alert.link ? (
          <Link key={i} to={alert.link} className={className}>
            {inner}
          </Link>
        ) : (
          <div key={i} className={className}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}

function ActivityFeed({ activity }) {
  if (!activity || activity.length === 0) {
    return (
      <div className="activity-empty">
        <i className="fas fa-inbox"></i>
        No activity recorded yet.
      </div>
    );
  }
  return (
    <div className="activity-feed">
      {activity.map((item, i) => (
        <div className="activity-item" key={i}>
          <span className="activity-icon">
            <i className={item.icon}></i>
          </span>
          <span className="activity-body">
            <span className="activity-text">{item.text}</span>
            <span className="activity-time">{item.time}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

function HealthMetricBar({ label, value, color }) {
  return (
    <div className="health-metric">
      <div className="health-metric-label">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="health-metric-track">
        <div
          className="health-metric-fill"
          style={{ width: `${value}%`, background: color }}
        ></div>
      </div>
    </div>
  );
}

function TrendRow({ label, value, max, display }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="trend-row">
      <span className="trend-row-label" title={label}>
        {label}
      </span>
      <span className="trend-row-track">
        <span className="trend-row-fill" style={{ width: `${pct}%` }}></span>
      </span>
      <span className="trend-row-value">{display ?? value}</span>
    </div>
  );
}

const QUICK_ACTIONS = [
  { text: "Add Student", icon: "fas fa-user-plus", to: "/student/add/" },
  { text: "Add Staff", icon: "fas fa-user-tie", to: "/staff/add" },
  { text: "Add Course", icon: "fas fa-graduation-cap", to: "/course/add" },
  { text: "Add Subject", icon: "fas fa-book-open", to: "/subject/add/" },
  { text: "Add Session", icon: "fas fa-calendar-plus", to: "/add_session/" },
  { text: "Notify Staff", icon: "fas fa-bullhorn", to: "/admin_notify_staff" },
  {
    text: "Notify Students",
    icon: "fas fa-bullhorn",
    to: "/admin_notify_student",
  },
];

/**
 * Admin dashboard — operational workspace. Answers "what needs my attention
 * today" first (attention grid + activity feed), then academic progress and
 * health trends, with KPI counters and quick actions as secondary context.
 * Backed entirely by /dashboard/admin/ (main_app/api/dashboard.py:admin_home).
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

  if (!stats) {
    return null;
  }

  const kpi = stats.kpi_metrics;
  const health = stats.health_trends;
  const progress = stats.academic_progress;

  return (
    <>
      {/* 1. KPI Metric Cards */}
      <div className="stats-grid">
        <StatCard
          icon="fas fa-user-graduate"
          tone="primary"
          number={kpi.total_students}
          label="Total Active Students"
          to="/student/manage/"
        />
        <StatCard
          icon="fas fa-users"
          tone="success"
          number={kpi.total_staff}
          label="Total Staff"
          to="/staff/manage/"
        />
        <StatCard
          icon="fas fa-book"
          tone="warning"
          number={kpi.total_subjects}
          label="Total Active Subjects"
        />
        <StatCard
          icon="fas fa-graduation-cap"
          tone="info"
          number={kpi.total_courses}
          label="Total Registered Courses"
          to="/course/manage/"
        />
        <StatCard
          icon="fas fa-calendar-alt"
          tone="accent"
          number={kpi.active_sessions}
          label="Active Academic Sessions"
        />
        <StatCard
          icon="fas fa-user-clock"
          tone="danger"
          number={kpi.pending_leave}
          label="Pending Leave Requests"
        />
        <StatCard
          icon="fas fa-chalkboard-teacher"
          tone="primary"
          number={kpi.classes_today}
          label="Active Classes Running Today"
        />
        <StatCard
          icon="fas fa-bullhorn"
          tone="success"
          number={kpi.notifications_today}
          label="Notifications Dispatched Today"
        />
      </div>

      {/* 2. Main Operational Split Pane */}
      <div className="row">
        <div className="col-lg-6">
          <SectionCard icon="fas fa-exclamation-triangle" title="Admin Attention Grid">
            <AttentionGrid alerts={stats.attention_alerts} />
          </SectionCard>
        </div>
        <div className="col-lg-6">
          <SectionCard icon="fas fa-history" title="Recent Activity">
            <ActivityFeed activity={stats.recent_activity} />
          </SectionCard>
        </div>
      </div>

      {/* 3. Institutional Health & Trend Matrices */}
      <div className="row">
        <div className="col-lg-6">
          <SectionCard icon="fas fa-heartbeat" title="Today's Institutional Health">
            <HealthMetricBar
              label="Present"
              value={health.today_attendance.present_pct}
              color="var(--success-color)"
            />
            <HealthMetricBar
              label="Absent"
              value={health.today_attendance.absent_pct}
              color="var(--danger-color)"
            />
            <HealthMetricBar
              label="Late"
              value={health.today_attendance.late_pct}
              color="var(--warning-color)"
            />
            <div className="health-stat-row">
              <span className="health-stat-label">Classes Completed Today</span>
              <span className="health-stat-value">
                {health.classes_completed.done} / {health.classes_completed.total}
              </span>
            </div>
            <div className="health-stat-row">
              <span className="health-stat-label">Student-to-Staff Ratio</span>
              <span className="health-stat-value">
                {health.student_staff_ratio}:1
              </span>
            </div>
            <div className="health-stat-row">
              <span className="health-stat-label">Average Cohort Size</span>
              <span className="health-stat-value">{health.avg_cohort_size}</span>
            </div>
          </SectionCard>
        </div>
        <div className="col-lg-6">
          <SectionCard icon="fas fa-chart-line" title="Micro Trend Lines">
            <p className="text-muted mb-2" style={{ fontSize: 12.5 }}>
              Intake by session (active students)
            </p>
            {health.intake_trend.length === 0 ? (
              <p className="text-muted" style={{ fontSize: 13 }}>
                No active intake data yet.
              </p>
            ) : (
              health.intake_trend.map((row) => (
                <TrendRow
                  key={row.label}
                  label={row.label}
                  value={row.count}
                  max={Math.max(...health.intake_trend.map((r) => r.count), 1)}
                />
              ))
            )}
            <p className="text-muted mb-2 mt-3" style={{ fontSize: 12.5 }}>
              Attendance — last 5 recorded days
            </p>
            {health.weekly_attendance.length === 0 ? (
              <p className="text-muted" style={{ fontSize: 13 }}>
                No attendance recorded yet.
              </p>
            ) : (
              health.weekly_attendance.map((row) => (
                <TrendRow
                  key={row.label}
                  label={row.label}
                  value={row.present_pct}
                  max={100}
                  display={`${row.present_pct}%`}
                />
              ))
            )}
          </SectionCard>
        </div>
      </div>

      {/* 4. Academic Progress & Milestone Scheduler */}
      <div className="row">
        <div className="col-lg-7">
          <SectionCard icon="fas fa-project-diagram" title="Cascade Promotion Monitor">
            {progress.courses.map((c) => (
              <div className="promo-course" key={c.course.id}>
                <div className="promo-course-name">{c.course.short_name}</div>
                {c.semesters.length === 0 ? (
                  <div className="promo-empty">No active students in this course.</div>
                ) : (
                  <div className="promo-semesters">
                    {c.semesters.map((s) => (
                      <span className="promo-chip" key={s.number}>
                        Sem {s.number}: {s.student_count} Stud.
                      </span>
                    ))}
                  </div>
                )}
                {c.ready_to_pass_out && (
                  <div className="promo-banner">
                    <i className="fas fa-exclamation-triangle"></i>
                    Semester Promotion Due: {c.course.short_name} Sem{" "}
                    {c.course.semesters} cohort is fully ready for advancement.
                    <Link
                      to={`/student/manage/course/${c.course.id}/`}
                      className="btn btn-warning btn-sm ms-auto"
                    >
                      Review &amp; Execute
                    </Link>
                  </div>
                )}
              </div>
            ))}
          </SectionCard>
        </div>
        <div className="col-lg-5">
          <SectionCard icon="fas fa-calendar-alt" title="Institutional Calendar">
            {progress.calendar.length === 0 ? (
              <div className="promo-empty">No upcoming milestones.</div>
            ) : (
              <div className="calendar-list">
                {progress.calendar.map((item, i) => (
                  <div className="calendar-item" key={i}>
                    <span className="calendar-date-badge">
                      {item.days_left === null ? "NOW" : `${item.days_left}d`}
                    </span>
                    <span className="calendar-item-label">{item.label}</span>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      {/* 5. Quick Actions */}
      <div className="row">
        <div className="col-12">
          <SectionCard icon="fas fa-bolt" title="Quick Actions">
            <div className="quick-actions-bar">
              {QUICK_ACTIONS.map((action) => (
                <Link key={action.text} to={action.to} className="btn btn-primary">
                  <i className={`${action.icon} me-2`}></i>
                  {action.text}
                </Link>
              ))}
            </div>
          </SectionCard>
        </div>
      </div>
    </>
  );
}

export default AdminDashboard;
