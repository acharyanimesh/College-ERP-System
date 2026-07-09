import { useEffect, useState } from "react";
import { sessionAPI, subjectAPI } from "../../api/academics";
import resultAPI from "../../api/results";
import { ListCard } from "../../components/ListCard";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/** Result Upload (staff_template/staff_add_result.html). */
function StaffAddResult() {
  usePageHeader({
    title: "Result Upload",
    breadcrumb: [{ text: "Result Upload" }],
  });
  const { addMessage } = useMessages();

  const [subjects, setSubjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [subject, setSubject] = useState("");
  const [session, setSession] = useState("");
  const [students, setStudents] = useState(null);
  const [student, setStudent] = useState("");
  const [test, setTest] = useState("");
  const [exam, setExam] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    subjectAPI.getAll().then(setSubjects).catch(() => {});
    sessionAPI.getAll().then(setSessions).catch(() => {});
  }, []);

  const fetchStudents = async () => {
    setStudents(null);
    if (!subject || !session) {
      window.alert("Please select session and subject");
      return;
    }
    try {
      const data = await resultAPI.getStudents({ subject, session });
      if (!data.length) {
        window.alert("No data to display");
        return;
      }
      setStudents(data);
      setStudent(String(data[0].id));
      setTest("");
      setExam("");
    } catch {
      window.alert("Error in fetching students");
    }
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await resultAPI.save({ student, subject, test, exam });
      addMessage(res?.updated ? "Scores Updated" : "Scores Saved", "success");
      setStudents(null);
    } catch {
      addMessage("Error Occured While Processing Form", "warning");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save}>
      <ListCard dark title="Result Upload">
        <div className="form-group">
          <label>Subject</label>
          <select
            className="form-control"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          >
            <option value="">----</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Session Year</label>
          <select
            className="form-control"
            value={session}
            onChange={(e) => setSession(e.target.value)}
          >
            <option value="">----</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                From {s.start_year} to {s.end_year}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          className="btn btn-primary btn-block w-100"
          onClick={fetchStudents}
        >
          Fetch Students
        </button>

        {students && (
          <div className="form-group">
            <hr />
            <div className="form-group">
              <label> Student List</label>
              <select
                className="form-control"
                value={student}
                onChange={(e) => setStudent(e.target.value)}
              >
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group row">
              <div className="col-md-6">
                <label> Test Score </label>
                <input
                  className="form-control"
                  placeholder="Test Score"
                  max={40}
                  min={0}
                  required
                  type="number"
                  value={test}
                  onChange={(e) => setTest(e.target.value)}
                />
              </div>
              <div className="col-md-6">
                <label> Exam Score </label>
                <input
                  className="form-control"
                  placeholder="Exam Score"
                  max={60}
                  min={0}
                  required
                  type="number"
                  value={exam}
                  onChange={(e) => setExam(e.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <button type="submit" className="btn btn-success" disabled={saving}>
                Save Result
              </button>
            </div>
          </div>
        )}
      </ListCard>
    </form>
  );
}

export default StaffAddResult;
