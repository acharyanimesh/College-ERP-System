import { useEffect, useState } from "react";
import { subjectAPI } from "../../api/academics";
import attendanceAPI from "../../api/attendance";
import { ListCard } from "../../components/ListCard";
import { usePageHeader } from "../../layouts/Layout";

const DIV_STYLES = `
.attendance_div_red{
    padding: 10px;
    background: #f44336;
    border: 3px solid white;
    text-align: center;
    color: #fff;
    border-radius: 30px;
    box-shadow: 1px 1px 1px grey;
    margin: 5px;
}
.attendance_div_green{
    padding: 10px;
    background: #4CAF50;
    border: 3px solid white;
    text-align: center;
    color: #fff;
    border-radius: 30px;
    box-shadow: 1px 1px 1px grey;
    margin: 5px;
}
`;

/**
 * Student "View Attendance" (student_template/student_view_attendance.html):
 * subject + date range → per-date present/absent pills.
 */
function StudentViewAttendance() {
  usePageHeader({
    title: "View Attendance",
    breadcrumb: [{ text: "View Attendance" }],
  });

  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [records, setRecords] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Only this student's course subjects come back for the student role.
    subjectAPI.getAll({ mine: 1 }).then(setSubjects).catch(() => {});
  }, []);

  const fetchAttendance = async () => {
    if (!subject || !startDate || !endDate) {
      window.alert("Please Select Subject and Date Range");
      return;
    }
    setRecords(null);
    setError("");
    try {
      const data = await attendanceAPI.getMyRecords({
        subject,
        start_date: startDate,
        end_date: endDate,
      });
      setRecords(data);
    } catch {
      setError("Error While Fetching Records");
    }
  };

  return (
    <ListCard dark title="View Attendance">
      <style>{DIV_STYLES}</style>
      <div className="form-group">
        <label>Select Subject</label>
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
      <div className="row">
        <div className="col-lg-6">
          <div className="form-group">
            <label>Start Date</label>
            <input
              type="date"
              className="form-control"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
        </div>
        <div className="col-lg-6">
          <div className="form-group">
            <label>End Date</label>
            <input
              type="date"
              className="form-control"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
        <button
          type="button"
          className="btn btn-success btn-block w-100"
          onClick={fetchAttendance}
        >
          Fetch Attendance Data
        </button>
      </div>

      <div style={{ overflow: "auto", maxHeight: 400 }} className="mt-3">
        <div className="row">
          {error && <div className="col-md-12 alert alert-danger">{error}</div>}
          {records && !records.length && (
            <div className="col-md-12 alert alert-danger">
              No Data For Specified Parameters
            </div>
          )}
          {records?.map((r, i) => (
            <div
              key={i}
              className={`col-lg-3 ${
                r.status ? "attendance_div_green" : "attendance_div_red"
              }`}
            >
              <b>{r.date}</b>
              <br />
              {r.status ? "Present" : "Absent"}
            </div>
          ))}
        </div>
      </div>
    </ListCard>
  );
}

export default StudentViewAttendance;
