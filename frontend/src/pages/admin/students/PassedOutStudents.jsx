import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/**
 * Passed-out records drill-down (passed_out_course_list.html →
 * passed_out_session_list.html → passed_out_student_list.html).
 */

export function PassedOutCourses() {
  usePageHeader({
    title: "Passed Out Students - Select Course",
    breadcrumb: [{ text: "Passed Out Students" }],
  });
  const { data: courseData } = useApi(() => studentAPI.passedOutCourses());

  return (
    <ListCard
      title="Passed Out Students - Select Course"
      action={<BackButton to="/student/manage/">Manage Students</BackButton>}
    >
      <p className="text-muted">
        Students who completed the final semester, kept on record per course.
        Select a course to view its passed-out batches by session.
      </p>
      <TileGrid>
        {courseData?.length ? (
          courseData.map((item) =>
            item.student_count ? (
              <Tile
                key={item.course.id}
                to={`/student/passed-out/course/${item.course.id}/`}
                label={item.course.short_name}
                title={item.course.name}
                badge={item.student_count}
                badgeClass="badge-success"
              />
            ) : (
              <Tile
                key={item.course.id}
                label={item.course.short_name}
                title={item.course.name}
                muted="No passed-out students"
              />
            )
          )
        ) : (
          <div className="col-12">
            <p>No courses available.</p>
          </div>
        )}
      </TileGrid>
    </ListCard>
  );
}

export function PassedOutSessions() {
  const { courseId } = useParams();
  const { data } = useApi(() => studentAPI.passedOutSessions(courseId), [courseId]);

  const course = data?.course;
  const title = course
    ? `Passed Out Students - ${course.short_name} (Select Session)`
    : "Passed Out Students";
  usePageHeader({ title, breadcrumb: [{ text: "Passed Out Students" }] });

  const hasAny = data?.session_data?.length || data?.no_session_count;

  return (
    <ListCard
      title={title}
      action={<BackButton to="/student/passed-out/">Back to Courses</BackButton>}
    >
      {data && !hasAny ? (
        <p className="text-muted">No passed-out students for this course yet.</p>
      ) : (
        <>
          <p className="text-muted">
            Passed-out batches of{" "}
            <strong title={course?.name}>{course?.short_name}</strong>, grouped
            by the session they were enrolled in.
          </p>
          <TileGrid>
            {data?.session_data?.map((item) => (
              <Tile
                key={item.session.id}
                to={`/student/passed-out/course/${courseId}/session/${item.session.id}/`}
                label={item.session.label}
                badge={item.student_count}
                badgeClass="badge-success"
              />
            ))}
          </TileGrid>
          {data?.no_session_count ? (
            <p className="text-muted mb-0">
              <i className="fas fa-info-circle"></i> {data.no_session_count}{" "}
              passed-out student(s) have no session recorded.
            </p>
          ) : null}
        </>
      )}
    </ListCard>
  );
}

export function PassedOutStudentList() {
  const { courseId, sessionId } = useParams();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const { data: students } = useApi(
    () => studentAPI.getPassedOut({ course: courseId, session: sessionId }),
    [courseId, sessionId]
  );

  const courseShort = students?.[0]?.course_short_name;
  const sessionLabel = students?.[0]?.session_label;
  const title =
    courseShort && sessionLabel
      ? `Passed Out Students - ${courseShort} (${sessionLabel})`
      : "Passed Out Students";
  usePageHeader({ title, breadcrumb: [{ text: "Passed Out Students" }] });

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
      action={
        <BackButton to={`/student/passed-out/course/${courseId}/`}>
          Back to Sessions
        </BackButton>
      }
    >
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by name, registration or roll number..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Roll No.</th>
            <th>Registration No.</th>
            <th>Full Name</th>
            <th>Shift</th>
            <th>Passed Out</th>
          </tr>
        </thead>
        <tbody>
          {students && !students.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No passed-out students in this session.
              </td>
            </tr>
          )}
          {students?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No students match your search.
              </td>
            </tr>
          )}
          {visible.map((s, i) => (
            <tr
              key={s.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/student/details/${s.id}`)}
            >
              <td>{i + 1}</td>
              <td>{s.roll_number || "—"}</td>
              <td>{s.registration_number || "—"}</td>
              <td>
                {s.first_name} {s.last_name}
              </td>
              <td>{s.shift_display}</td>
              <td>{s.passed_out_date || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}
