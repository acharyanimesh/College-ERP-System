import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import notificationAPI from "../../../api/notifications";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";
import NotificationModal from "./NotificationModal";

/**
 * Send Notifications To Students, three screens
 * (student_notification.html → notify_student_semester_list.html →
 * notify_student_list.html): search-any-student + course tiles, then
 * semester tiles, then the student table — all with the send modal.
 */

export function NotifyStudent() {
  usePageHeader({
    title: "Send Notifications To Students",
    breadcrumb: [{ text: "Notify Students" }],
  });
  const { data } = useApi(() => notificationAPI.getStudentBrowse());
  const [query, setQuery] = useState("");
  const [targetId, setTargetId] = useState(null);

  const q = query.toLowerCase().trim();
  const results = useMemo(() => {
    if (!q || !data?.search_students) return [];
    return data.search_students.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        String(s.roll || "").toLowerCase().includes(q)
    );
  }, [data, q]);

  return (
    <ListCard title="Send Notifications To Students">
      <div className="form-group" style={{ maxWidth: 420 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search any student by name or roll number to notify..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {q ? (
        /* Search results (shown only while searching) */
        <table className="table table-bordered table-hover">
          <thead className="thead-dark">
            <tr>
              <th>#</th>
              <th>Full Name</th>
              <th>Course</th>
              <th>Semester</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {results.length ? (
              results.map((s, i) => (
                <tr key={s.id}>
                  <td>{i + 1}</td>
                  <td>{s.name}</td>
                  <td title={s.course_full}>{s.course}</td>
                  <td>{s.semester}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={() => setTargetId(s.id)}
                    >
                      Send Notification
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="text-center">
                  No students match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      ) : (
        /* Browse by course (shown when not searching) */
        <>
          <p className="text-muted">
            Select a course, then a semester, to notify its students &mdash; or
            search above.
          </p>
          <TileGrid>
            {data?.course_data?.length ? (
              data.course_data.map((item) => (
                <Tile
                  key={item.course.id}
                  to={`/admin_notify_student/course/${item.course.id}/`}
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
        </>
      )}

      <NotificationModal
        show={targetId !== null}
        onClose={() => setTargetId(null)}
        onSend={(message) => notificationAPI.sendToStudent(targetId, message)}
      />
    </ListCard>
  );
}

export function NotifyStudentSemesters() {
  const { courseId } = useParams();
  const { data } = useApi(
    () => notificationAPI.getStudentSemesters(courseId),
    [courseId]
  );
  const course = data?.course;
  const title = course
    ? `Notify Students - ${course.short_name} (Select Semester)`
    : "Notify Students";
  usePageHeader({ title, breadcrumb: [{ text: "Notify Students" }] });

  return (
    <ListCard
      title={title}
      action={<BackButton to="/admin_notify_student">Back to Courses</BackButton>}
    >
      <p className="text-muted">
        Select a semester of{" "}
        <strong title={course?.name}>{course?.short_name}</strong> to notify
        its students (both shifts together).
      </p>
      <TileGrid>
        {data?.semester_data?.map((item) =>
          item.student_count ? (
            <Tile
              key={item.number}
              to={`/admin_notify_student/course/${courseId}/semester/${item.number}/`}
              label={`Semester ${item.number}`}
              badge={item.student_count}
            />
          ) : (
            <Tile
              key={item.number}
              label={`Semester ${item.number}`}
              muted="No students"
            />
          )
        )}
      </TileGrid>
    </ListCard>
  );
}

export function NotifyStudentList() {
  const { courseId, semester } = useParams();
  const [query, setQuery] = useState("");
  const [targetId, setTargetId] = useState(null);

  const { data: students } = useApi(
    () => notificationAPI.getStudentRecipients({ course: courseId, semester }),
    [courseId, semester]
  );

  const courseShort = students?.[0]?.course_short_name;
  const title = courseShort
    ? `Notify Students - ${courseShort} - Semester ${semester}`
    : "Notify Students";
  usePageHeader({ title, breadcrumb: [{ text: "Notify Students" }] });

  const visible = useMemo(() => {
    if (!students) return [];
    const q = query.toLowerCase().trim();
    if (!q) return students;
    return students.filter(
      (s) =>
        `${s.first_name} ${s.last_name}`.toLowerCase().includes(q) ||
        (s.roll_number || "").toLowerCase().includes(q)
    );
  }, [students, query]);

  return (
    <ListCard
      title={title}
      scrollBody
      action={
        <BackButton to={`/admin_notify_student/course/${courseId}/`}>
          Back to Semesters
        </BackButton>
      }
    >
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by name or roll number..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Roll No.</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Course</th>
            <th>Shift</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {students && !students.length && (
            <tr>
              <td colSpan={7} className="text-center">
                No students in this semester.
              </td>
            </tr>
          )}
          {students?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={7} className="text-center">
                No students match your search.
              </td>
            </tr>
          )}
          {visible.map((s, i) => (
            <tr key={s.id}>
              <td>{i + 1}</td>
              <td>{s.roll_number || "—"}</td>
              <td>
                {s.first_name} {s.last_name}
              </td>
              <td>{s.email}</td>
              <td title={s.course_name}>{s.course_short_name}</td>
              <td>{s.shift_display}</td>
              <td>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  onClick={() => setTargetId(s.user_id ?? s.id)}
                >
                  Send Notification
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <NotificationModal
        show={targetId !== null}
        onClose={() => setTargetId(null)}
        onSend={(message) => notificationAPI.sendToStudent(targetId, message)}
      />
    </ListCard>
  );
}
