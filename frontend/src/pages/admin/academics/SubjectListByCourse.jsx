import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { courseAPI, subjectAPI } from "../../../api/academics";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** 'ABC 123' subject-code formatting from forms.py, applied as the user types. */
export function formatSubjectCode(value) {
  const code = (value || "").toUpperCase().replace(/\s+/g, "");
  return code.length > 3 ? `${code.slice(0, 3)} ${code.slice(3)}` : code;
}

/**
 * Manage Subjects of one course+semester (subject_list_by_course.html):
 * inline quick-add form + searchable subject table.
 */
function SubjectListByCourse() {
  const { courseId, semester } = useParams();
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");
  const [newSubject, setNewSubject] = useState({ name: "", code: "", credit_hours: "" });
  const [submitting, setSubmitting] = useState(false);

  const { data: course } = useApi(() => courseAPI.get(courseId), [courseId]);
  const { data: subjects, reload } = useApi(
    () => subjectAPI.getAll({ course: courseId, semester }),
    [courseId, semester]
  );

  const title = course
    ? `Manage Subjects - ${course.short_name} - Semester ${semester}`
    : "Manage Subjects";
  usePageHeader({ title, breadcrumb: [{ text: "Manage Subjects" }] });

  const visible = useMemo(() => {
    if (!subjects) return [];
    const q = query.toLowerCase().trim();
    if (!q) return subjects;
    return subjects.filter(
      (s) =>
        (s.name || "").toLowerCase().includes(q) ||
        (s.code || "").toLowerCase().includes(q)
    );
  }, [subjects, query]);

  const addSubject = async (e) => {
    e.preventDefault();
    if (!newSubject.name.trim()) {
      addMessage("Please enter a subject name.", "danger");
      return;
    }
    setSubmitting(true);
    try {
      await subjectAPI.create({
        ...newSubject,
        code: formatSubjectCode(newSubject.code),
        courses: [{ course: Number(courseId), semester: Number(semester) }],
      });
      addMessage(
        `Subject '${newSubject.name}' added to ${course?.short_name} - Semester ${semester}.`,
        "success"
      );
      setNewSubject({ name: "", code: "", credit_hours: "" });
      reload();
    } catch (err) {
      addMessage(
        "Could not add subject: " + (err.response?.data?.detail || "error"),
        "danger"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (subject) => {
    if (!window.confirm("Are you sure you want to delete this ?")) return;
    try {
      await subjectAPI.delete(subject.id);
      addMessage("Subject deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Could not delete the subject.", "danger");
    }
  };

  return (
    <ListCard
      title={title}
      scrollBody
      action={
        <BackButton to={`/subject/manage/course/${courseId}/`}>
          Back to Semesters
        </BackButton>
      }
    >
      <form onSubmit={addSubject} className="mb-4">
        <label className="font-weight-bold d-block mb-3">
          Add Subject to{" "}
          <span title={course?.name}>{course?.short_name}</span> - Semester{" "}
          {semester}
        </label>
        <div className="row">
          <div className="form-group col-md-8 col-lg-6 mb-3">
            <label className="mb-1">Subject Name</label>
            <input
              type="text"
              className="form-control"
              required
              value={newSubject.name}
              onChange={(e) => setNewSubject((s) => ({ ...s, name: e.target.value }))}
            />
          </div>
        </div>
        <div className="row">
          <div className="form-group col-md-4 col-lg-3 mb-3">
            <label className="mb-1">Code</label>
            <input
              type="text"
              className="form-control text-uppercase"
              value={newSubject.code}
              onChange={(e) =>
                setNewSubject((s) => ({ ...s, code: formatSubjectCode(e.target.value) }))
              }
            />
          </div>
          <div className="form-group col-md-4 col-lg-3 mb-3">
            <label className="mb-1">Credit Hours</label>
            <input
              type="number"
              min={0}
              className="form-control"
              value={newSubject.credit_hours}
              onChange={(e) =>
                setNewSubject((s) => ({ ...s, credit_hours: e.target.value }))
              }
            />
          </div>
        </div>
        <button type="submit" className="btn btn-success" disabled={submitting}>
          <i className="fas fa-plus"></i> Add Subject
        </button>
      </form>
      <hr />
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by code or subject name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Code</th>
            <th>Subject</th>
            <th>Credit Hours</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {subjects && !subjects.length && (
            <tr>
              <td colSpan={5} className="text-center">
                No subjects in this course.
              </td>
            </tr>
          )}
          {subjects?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={5} className="text-center">
                No subjects match your search.
              </td>
            </tr>
          )}
          {visible.map((subject, i) => (
            <tr
              key={subject.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/subject/view/${subject.id}`)}
            >
              <td>{i + 1}</td>
              <td>{subject.code || "—"}</td>
              <td>{subject.name}</td>
              <td>{subject.credit_hours || "—"}</td>
              <td className="text-nowrap" onClick={(e) => e.stopPropagation()}>
                <Link
                  to={`/subject/edit/${subject.id}`}
                  className="btn btn-sm btn-info"
                  title="Edit"
                >
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(subject)}
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

export default SubjectListByCourse;
