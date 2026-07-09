import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import attendanceAPI from "../../../api/attendance";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/**
 * Admin "Fetch Attendance" drill-down: course tiles →
 * student table → per-student subject summary
 * (admin_view_attendance.html / attendance_student_list.html /
 * student_attendance_detail.html).
 */

export function AdminViewAttendance() {
  usePageHeader({
    title: "Fetch Attendance - Select Course",
    breadcrumb: [{ text: "Fetch Attendance" }],
  });
  const { data: courseData } = useApi(() => attendanceAPI.adminCourses());

  return (
    <ListCard title="Fetch Attendance - Select Course">
      <p className="text-muted">Select a course to view its students' attendance.</p>
      <TileGrid>
        {courseData?.length ? (
          courseData.map((item) => (
            <Tile
              key={item.course.id}
              to={`/attendance/view/course/${item.course.id}/`}
              label={item.course.short_name}
              title={item.course.name}
              badge={item.student_count}
            />
          ))
        ) : (
          <div className="col-12">
            <p>No courses available.</p>
          </div>
        )}
      </TileGrid>
    </ListCard>
  );
}

export function AttendanceStudentList() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const { data } = useApi(() => attendanceAPI.adminStudents(courseId), [courseId]);
  const course = data?.course;
  const students = data?.students;

  const title = course ? `Fetch Attendance - ${course.short_name}` : "Fetch Attendance";
  usePageHeader({ title, breadcrumb: [{ text: "Fetch Attendance" }] });

  const visible = useMemo(() => {
    if (!students) return [];
    const q = query.toLowerCase().trim();
    if (!q) return students;
    return students.filter(
      (s) =>
        `${s.first_name} ${s.last_name}`.toLowerCase().includes(q) ||
        (s.registration_number || "").toLowerCase().includes(q) ||
        (s.roll_number || "").toLowerCase().includes(q)
    );
  }, [students, query]);

  return (
    <ListCard
      title={title}
      scrollBody
      action={<BackButton to="/attendance/view/">Back to Courses</BackButton>}
    >
      <p className="text-muted">Click a student to view their attendance by subject.</p>
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by name, registration or roll number..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 700 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Registration No.</th>
            <th>Roll No.</th>
            <th>Full Name</th>
            <th>Email</th>
          </tr>
        </thead>
        <tbody>
          {students && !students.length && (
            <tr>
              <td colSpan={5} className="text-center">
                No students enrolled in this course.
              </td>
            </tr>
          )}
          {students?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={5} className="text-center">
                No students match your search.
              </td>
            </tr>
          )}
          {visible.map((s, i) => (
            <tr
              key={s.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/attendance/view/student/${s.id}/`)}
            >
              <td>{i + 1}</td>
              <td>{s.registration_number || "—"}</td>
              <td>{s.roll_number || "—"}</td>
              <td>
                {s.first_name} {s.last_name}
              </td>
              <td>{s.email}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export function StudentAttendanceDetail() {
  const { studentId } = useParams();
  const { data } = useApi(() => attendanceAPI.studentSummary(studentId), [studentId]);
  const student = data?.student;

  const title = student
    ? `${student.first_name} ${student.last_name} — Attendance`
    : "Student Attendance";
  usePageHeader({ title, breadcrumb: [{ text: "Fetch Attendance" }] });

  if (!data) return null;

  return (
    <ListCard
      dark
      title={title}
      action={
        <BackButton to={`/attendance/view/course/${student.course}/`}>
          Back to Students
        </BackButton>
      }
    >
      <dl className="row">
        <dt className="col-sm-3">Registration Number</dt>
        <dd className="col-sm-9">{student.registration_number || "—"}</dd>
        <dt className="col-sm-3">Roll Number</dt>
        <dd className="col-sm-9">{student.roll_number || "—"}</dd>
        <dt className="col-sm-3">Course</dt>
        <dd className="col-sm-9" title={student.course_name}>
          {student.course_short_name || "—"}
        </dd>
      </dl>

      <hr />

      <h5>Attendance by Subject</h5>
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Subject</th>
            <th>Total Classes</th>
            <th>Present</th>
            <th>Absent</th>
            <th>Percentage</th>
          </tr>
        </thead>
        <tbody>
          {data.attendance_summary?.length ? (
            data.attendance_summary.map((item, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td>{item.subject}</td>
                <td>{item.total}</td>
                <td>{item.present}</td>
                <td>{item.absent}</td>
                <td>
                  <span
                    className={`badge ${
                      item.percentage >= 75
                        ? "badge-success"
                        : item.percentage >= 50
                          ? "badge-warning"
                          : "badge-danger"
                    }`}
                  >
                    {item.percentage}%
                  </span>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={6} className="text-center">
                No attendance records found for this student.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </ListCard>
  );
}
