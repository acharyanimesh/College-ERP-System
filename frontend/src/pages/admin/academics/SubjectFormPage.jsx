import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { courseAPI, subjectAPI } from "../../../api/academics";
import { FormCard, TextField, useFormSubmit } from "../../../components/forms";
import { usePageHeader, useMessages } from "../../../layouts/Layout";
import { formatSubjectCode } from "./SubjectListByCourse";

/**
 * Add/Edit Subject (add/edit_subject_template.html): name/code/credit hours
 * plus the per-course semester table — enter a semester number to place the
 * subject in that course, leave blank to skip it.
 */
function SubjectFormPage({ edit = false }) {
  const pageTitle = edit ? "Edit Subject" : "Add Subject";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });
  const { addMessage } = useMessages();
  const navigate = useNavigate();
  const { subjectId } = useParams();

  const [fields, setFields] = useState({ name: "", code: "", credit_hours: "" });
  const [courses, setCourses] = useState([]);
  // courseId → semester string ('' = not in this course)
  const [semesters, setSemesters] = useState({});

  useEffect(() => {
    courseAPI.getAll().then(setCourses).catch(() => {});
  }, []);

  useEffect(() => {
    if (!edit) return;
    subjectAPI
      .get(subjectId)
      .then((s) => {
        setFields({ name: s.name, code: s.code || "", credit_hours: s.credit_hours || "" });
        const map = {};
        (s.courses || []).forEach((row) => {
          map[row.course] = String(row.semester ?? "");
        });
        setSemesters(map);
      })
      .catch(() => addMessage("Could not load the subject.", "danger"));
  }, [edit, subjectId, addMessage]);

  const setField = (name, value) => {
    if (name === "code") value = formatSubjectCode(value);
    setFields((f) => ({ ...f, [name]: value }));
  };

  const { submitting, errors, nonFieldError, handleSubmit } = useFormSubmit(
    () => {
      const payload = {
        ...fields,
        courses: Object.entries(semesters)
          .filter(([, sem]) => String(sem).trim() !== "")
          .map(([course, sem]) => ({ course: Number(course), semester: Number(sem) })),
      };
      return edit ? subjectAPI.update(subjectId, payload) : subjectAPI.create(payload);
    },
    {
      onSuccess: () => {
        addMessage(
          edit ? "Subject updated successfully!" : "Subject added successfully!",
          "success"
        );
        navigate("/course/manage/");
      },
    }
  );

  return (
    <FormCard
      title={pageTitle}
      onSubmit={handleSubmit}
      buttonText={edit ? "Update Subject" : "Add Subject"}
      nonFieldError={nonFieldError}
      submitting={submitting}
    >
      <TextField label="Name" name="name" value={fields.name} onChange={setField} error={errors.name} required />
      <TextField
        label="Subject Code"
        name="code"
        value={fields.code}
        onChange={setField}
        error={errors.code}
        className="form-control text-uppercase"
      />
      <TextField
        label="Credit hours"
        name="credit_hours"
        type="number"
        min={0}
        value={fields.credit_hours}
        onChange={setField}
        error={errors.credit_hours}
      />

      <hr />
      <label className="font-weight-bold mb-1">Courses &amp; Semesters</label>
      <p className="text-muted">
        Enter the semester number for each course this subject is taught in.
        Leave a course blank to skip it. The same subject can sit in a{" "}
        <em>different</em> semester in each course.
      </p>
      <div className="table-responsive">
        <table className="table table-bordered table-hover">
          <thead className="thead-dark">
            <tr>
              <th>Course</th>
              <th style={{ width: 200 }}>Semester</th>
            </tr>
          </thead>
          <tbody>
            {courses.length ? (
              courses.map((course) => (
                <tr key={course.id}>
                  <td title={course.name}>{course.short_name}</td>
                  <td>
                    <input
                      type="number"
                      className="form-control"
                      min={1}
                      max={course.semesters || undefined}
                      placeholder="— not in this course —"
                      value={semesters[course.id] ?? ""}
                      onChange={(e) =>
                        setSemesters((m) => ({ ...m, [course.id]: e.target.value }))
                      }
                    />
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={2} className="text-center">
                  No courses available. Add a course first.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </FormCard>
  );
}

export default SubjectFormPage;
