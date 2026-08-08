import { useEffect, useState } from "react";
import { subjectAPI } from "../../api/academics";
import attendanceAPI from "../../api/attendance";
import { ListCard } from "../../components/ListCard";
import { usePageHeader } from "../../layouts/Layout";

const RESULT_STYLES = `
.attendance-result{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 20px;
    border-radius: 10px;
    border: 1px solid rgba(0, 0, 0, 0.08);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    color: #fff;
}
.attendance-result-present{ background: #4CAF50; }
.attendance-result-absent{ background: #f44336; }
.attendance-result-icon{
    font-size: 30px;
    line-height: 1;
    flex-shrink: 0;
}
.attendance-result-status{
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0;
}
.attendance-result-meta{
    margin: 2px 0 0;
    opacity: 0.9;
    font-size: 0.9rem;
}
`;

/** ISO (yyyy-mm-dd) date for the <input type="date"> max attribute. */
function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now - offset).toISOString().slice(0, 10);
}

/**
 * Student "View Attendance" (student_template/student_view_attendance.html):
 * subject + one specific date → whether they were marked present that day.
 */
function StudentViewAttendance() {
  usePageHeader({
    title: "View Attendance",
    breadcrumb: [{ text: "View Attendance" }],
  });

  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState("");
  const [date, setDate] = useState("");
  const [records, setRecords] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // `mine` returns only the subjects of the student's course at their
    // current semester (see api/academics.subject_list).
    subjectAPI.getAll({ mine: 1 }).then(setSubjects).catch(() => {});
  }, []);

  const fetchAttendance = async () => {
    if (!subject || !date) {
      setError("Please select a subject and a date.");
      setRecords(null);
      return;
    }
    setRecords(null);
    setError("");
    setLoading(true);
    try {
      setRecords(await attendanceAPI.getMyRecords({ subject, date }));
    } catch {
      setError("Error While Fetching Records");
    } finally {
      setLoading(false);
    }
  };

  const subjectName = subjects.find((s) => String(s.id) === String(subject))?.name;

  return (
    <ListCard dark title="View Attendance">
      <style>{RESULT_STYLES}</style>
      <div className="row g-3 align-items-end">
        <div className="col-lg-5 col-md-6">
          <div className="form-group mb-0">
            <label htmlFor="subject">Select Subject</label>
            <select
              id="subject"
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
        </div>
        <div className="col-lg-4 col-md-6">
          <div className="form-group mb-0">
            <label htmlFor="attendance-date">Date</label>
            <input
              id="attendance-date"
              type="date"
              className="form-control"
              value={date}
              max={todayIso()}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
        </div>
        <div className="col-lg-3 col-md-12">
          <button
            type="button"
            className="btn btn-success w-100"
            onClick={fetchAttendance}
            disabled={loading}
          >
            {loading ? "Fetching..." : "Fetch Attendance"}
          </button>
        </div>
      </div>

      <div className="mt-4">
        {error && <div className="alert alert-danger">{error}</div>}
        {records && !records.length && (
          <div className="alert alert-warning mb-0">
            No attendance was recorded for {subjectName || "this subject"} on{" "}
            {date}.
          </div>
        )}
        {records?.map((r, i) => (
          <div
            key={i}
            className={`attendance-result ${
              r.status ? "attendance-result-present" : "attendance-result-absent"
            } ${i ? "mt-3" : ""}`}
          >
            <i
              className={`attendance-result-icon fas fa-${
                r.status ? "check-circle" : "times-circle"
              }`}
            ></i>
            <div>
              <p className="attendance-result-status">
                {r.status ? (r.late ? "Present (Late)" : "Present") : "Absent"}
              </p>
              <p className="attendance-result-meta">
                {subjectName ? `${subjectName} — ` : ""}
                {r.date}
              </p>
            </div>
          </div>
        ))}
      </div>
    </ListCard>
  );
}

export default StudentViewAttendance;
