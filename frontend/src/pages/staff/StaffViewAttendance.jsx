import { useState } from "react";
import attendanceAPI from "../../api/attendance";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";
import ClassPicker from "./ClassPicker";

/** View Attendance, read-only (staff_template/staff_view_attendance.html). */
function StaffViewAttendance() {
  usePageHeader({
    title: "View Attendance",
    breadcrumb: [{ text: "View Attendance" }],
  });
  const { data: picker } = useApi(() => attendanceAPI.getPicker());

  const [sel, setSel] = useState({ shift: "morning", subject: "", course: "", semester: "" });
  const [error, setError] = useState("");
  const [dates, setDates] = useState(null);
  const [dateId, setDateId] = useState("");
  const [students, setStudents] = useState(null);

  const onPick = (patch) => {
    setSel((s) => ({ ...s, ...patch }));
    setDates(null);
    setStudents(null);
  };

  const loadStudents = async (attendanceId) => {
    setStudents(null);
    if (!attendanceId) return;
    try {
      setStudents(await attendanceAPI.getStudentRecords(attendanceId));
    } catch {
      setError("Error in fetching students");
    }
  };

  const fetchAttendance = async () => {
    const { subject, course, semester, shift } = sel;
    if (!subject || !course || !semester || !shift) {
      setError("Kindly choose subject, course, semester and shift");
      setDates(null);
      return;
    }
    try {
      const data = await attendanceAPI.getAttendance({
        subject,
        course,
        semester,
        shift,
        include_locked: "1",
      });
      if (data.length) {
        setError("");
        setDates(data);
        setDateId(String(data[0].id));
        loadStudents(data[0].id);
      } else {
        setError("No attendance has been recorded for this class yet.");
        setDates(null);
      }
    } catch {
      setError("Error while fetching data");
      setDates(null);
    }
  };

  const badge = (s) =>
    !s.status
      ? ["badge-danger", "Absent"]
      : s.late
        ? ["badge-warning", "Late"]
        : ["badge-success", "Present"];

  return (
    <ListCard dark title="View Attendance">
      <ClassPicker
        picker={picker}
        value={sel}
        onChange={onPick}
        restrictActive={false}
        classHelp="Pick a shift and subject first; classes you teach this subject in are listed."
      />

      {error && <div className="alert alert-danger">{error}</div>}
      <div className="form-group">
        <button type="button" className="btn btn-success btn-block w-100" onClick={fetchAttendance}>
          Fetch Attendance
        </button>
      </div>

      {dates && (
        <div className="form-group">
          <div className="form-group">
            <label>Attendance Date</label>
            <select
              className="form-control"
              value={dateId}
              onChange={(e) => {
                setDateId(e.target.value);
                loadStudents(e.target.value);
              }}
            >
              {dates.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.attendance_date}
                </option>
              ))}
            </select>
          </div>

          {students &&
            (students.length ? (
              <>
                <hr />
                <div className="form-group">
                  <label>Student Attendance</label>
                  <div className="list-group student-attendance-list">
                    {students.map((s) => {
                      const [cls, text] = badge(s);
                      return (
                        <div
                          key={s.id}
                          className="list-group-item d-flex justify-content-between align-items-center flex-wrap"
                        >
                          <span className="student-name">
                            {s.roll_number && <span className="student-roll">{s.roll_number}</span>}
                            {s.name}
                          </span>
                          <span className={`badge ${cls} status-badge`}>{text}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <>
                <hr />
                <p className="text-muted">No students found for this date.</p>
              </>
            ))}
        </div>
      )}
    </ListCard>
  );
}

export default StaffViewAttendance;
