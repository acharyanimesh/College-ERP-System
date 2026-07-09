import { useEffect, useState } from "react";
import { sessionAPI, subjectAPI } from "../../api/academics";
import resultAPI from "../../api/results";
import { ListCard } from "../../components/ListCard";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Edit Student's Result (staff_template/edit_student_result.html +
 * EditResultView): pick session/subject → students load → picking a student
 * fetches their scores → test/exam inputs appear → update.
 */
function EditStudentResult() {
  usePageHeader({
    title: "Edit Student's Result",
    breadcrumb: [{ text: "Edit Result" }],
  });
  const { addMessage } = useMessages();

  const [subjects, setSubjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [sessionYear, setSessionYear] = useState("");
  const [subject, setSubject] = useState("");
  const [students, setStudents] = useState([]);
  const [student, setStudent] = useState("");
  const [scores, setScores] = useState(null); // { test, exam } once fetched
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    subjectAPI.getAll().then(setSubjects).catch(() => {});
    sessionAPI.getAll().then(setSessions).catch(() => {});
  }, []);

  const fetchStudents = async (subjectVal, sessionVal) => {
    setStudents([]);
    setStudent("");
    setScores(null);
    if (!subjectVal || !sessionVal) return;
    try {
      const data = await resultAPI.getStudents({
        subject: subjectVal,
        session: sessionVal,
      });
      if (!data.length) {
        window.alert("No data to display");
        return;
      }
      setStudents(data);
    } catch {
      window.alert("Error in fetching students");
    }
  };

  const fetchResult = async (studentVal) => {
    setScores(null);
    if (!studentVal || !subject) return;
    try {
      const data = await resultAPI.fetch({ subject, student: studentVal });
      setScores({ test: data.test, exam: data.exam });
    } catch {
      window.alert("No data to display");
    }
  };

  const update = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await resultAPI.update({
        session_year: sessionYear,
        subject,
        student,
        test: scores.test,
        exam: scores.exam,
      });
      addMessage("Result Updated", "success");
      setScores(null);
      setStudent("");
    } catch {
      addMessage("Result Could Not Be Updated", "danger");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={update}>
      <ListCard dark title="Edit Student's Result">
        <div className="form-group">
          <label>Session Year:</label>
          <select
            className="form-control"
            value={sessionYear}
            onChange={(e) => {
              setSessionYear(e.target.value);
              fetchStudents(subject, e.target.value);
            }}
          >
            <option value="">---------</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                From {s.start_year} to {s.end_year}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Subject:</label>
          <select
            className="form-control"
            value={subject}
            onChange={(e) => {
              setSubject(e.target.value);
              fetchStudents(e.target.value, sessionYear);
            }}
          >
            <option value="">---------</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Student:</label>
          <select
            className="form-control"
            value={student}
            onChange={(e) => {
              setStudent(e.target.value);
              fetchResult(e.target.value);
            }}
          >
            <option value="">Select Student</option>
            {students.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        {scores && (
          <>
            <div className="form-group">
              <label>Test:</label>
              <input
                type="number"
                className="form-control"
                value={scores.test}
                onChange={(e) => setScores((sc) => ({ ...sc, test: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label>Exam:</label>
              <input
                type="number"
                className="form-control"
                value={scores.exam}
                onChange={(e) => setScores((sc) => ({ ...sc, exam: e.target.value }))}
              />
            </div>
            <button type="submit" className="btn btn-primary btn-block w-100" disabled={saving}>
              Update Result
            </button>
          </>
        )}
      </ListCard>
    </form>
  );
}

export default EditStudentResult;
