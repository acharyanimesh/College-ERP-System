import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

const SHIFT_LABELS = { morning: "Morning Shift", day: "Day Shift" };

/**
 * Manage Students — student table for one course/semester/shift
 * (student_list_by_course.html): client-side search over name /
 * registration / roll number, row click to details, edit/delete actions.
 */
function StudentList() {
  const { courseId, semester, shift } = useParams();
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");

  const { data: students, reload } = useApi(
    () => studentAPI.getAll({ course: courseId, semester, shift }),
    [courseId, semester, shift]
  );

  const shiftLabel = SHIFT_LABELS[shift] || shift;
  const courseShort = students?.[0]?.course_short_name;
  const title = `Manage Students - ${courseShort || ""} - Semester ${semester} (${shiftLabel})`;
  usePageHeader({ title, breadcrumb: [{ text: "Manage Students" }] });

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

  const remove = async (student) => {
    if (!window.confirm("Are you sure about this ?")) return;
    try {
      await studentAPI.delete(student.id);
      addMessage("Student deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Could not delete the student.", "danger");
    }
  };

  const resend = async (student) => {
    try {
      await studentAPI.resendVerification(student.id);
      addMessage("Verification email sent.", "success");
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not send the verification email.",
        "danger"
      );
    }
  };

  return (
    <ListCard
      title={title}
      scrollBody
      action={
        <BackButton to={`/student/manage/course/${courseId}/semester/${semester}/`}>
          Back to Shifts
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
            <th>Registration No.</th>
            <th>Roll No.</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Course</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {students && !students.length && (
            <tr>
              <td colSpan={8} className="text-center">
                No students enrolled in this course.
              </td>
            </tr>
          )}
          {students?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={8} className="text-center">
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
              <td>{s.registration_number || "—"}</td>
              <td>{s.roll_number || "—"}</td>
              <td>
                {s.first_name} {s.last_name}
              </td>
              <td>{s.email}</td>
              <td title={s.course_name}>{s.course_short_name}</td>
              <td>
                {s.verified ? (
                  <span className="badge badge-success">Verified</span>
                ) : (
                  <span className="badge badge-warning">Pending verification</span>
                )}
              </td>
              <td className="text-nowrap" onClick={(e) => e.stopPropagation()}>
                {!s.verified && (
                  <>
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      title="Resend verification email"
                      onClick={() => resend(s)}
                    >
                      <i className="fas fa-paper-plane"></i>
                    </button>{" "}
                  </>
                )}
                <Link
                  to={`/student/edit/${s.id}`}
                  className="btn btn-sm btn-info"
                  title="Edit"
                >
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(s)}
                >
                  <i className="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default StudentList;
