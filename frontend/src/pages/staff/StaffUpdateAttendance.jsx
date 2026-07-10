import { useState } from "react";
import attendanceAPI from "../../api/attendance";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";
import ClassPicker from "./ClassPicker";
import { StatusButtons, statusPayload } from "./StaffTakeAttendance";

/** Update Attendance (staff_template/staff_update_attendance.html). */
function StaffUpdateAttendance() {
  usePageHeader({
    title: "Update Attendance",
    breadcrumb: [{ text: "Update Attendance" }],
  });
  const { data: picker } = useApi(() => attendanceAPI.getPicker());

  const [sel, setSel] = useState({ shift: "morning", subject: "", course: "", semester: "" });
  const [error, setError] = useState("");
  const [dates, setDates] = useState(null); // [{id, attendance_date}]
  const [dateId, setDateId] = useState("");
  const [students, setStudents] = useState(null);
  const [statuses, setStatuses] = useState({});
  const [saving, setSaving] = useState(false);

  const onPick = (patch) => {
    setSel((s) => ({ ...s, ...patch }));
    setDates(null);
    setStudents(null);
  };

  const loadStudents = async (attendanceId) => {
    setStudents(null);
    if (!attendanceId) return;
    try {
      const data = await attendanceAPI.getStudentRecords(attendanceId);
      setStudents(data);
      const initial = {};
      data.forEach((s) => {
        initial[s.id] = s.status ? (s.late ? "late" : "present") : "absent";
      });
      setStatuses(initial);
    } catch {
      window.alert("Error in fetching students");
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
      const data = await attendanceAPI.getAttendance({ subject, course, semester, shift });
      if (data.length) {
        setError("");
        setDates(data);
        setDateId(String(data[0].id));
        loadStudents(data[0].id);
      } else {
        setError("No Attendance Date Found For Specified Data");
        setDates(null);
      }
    } catch {
      window.alert("Error While Fetching Data");
      setDates(null);
    }
  };

  const save = async () => {
    if (
      !window.confirm(
        "Confirm this attendance? Once saved it becomes permanent and cannot be changed again."
      )
    ) {
      return;
    }
    setSaving(true);
    try {
      await attendanceAPI.update(dateId, {
        student_ids: statusPayload(students, statuses),
      });
      window.alert(
        "Attendance confirmed. It is now permanent and can no longer be changed."
      );
      setDates(null);
      setStudents(null);
    } catch (err) {
      const code = err.response?.data?.code;
      if (code === "NOT_ASSIGNED") {
        window.alert("You are not assigned to this subject, so you cannot update its attendance.");
      } else if (code === "LOCKED") {
        window.alert("This attendance has already been confirmed and cannot be changed.");
        setDates(null);
        setStudents(null);
      } else {
        window.alert("Error in saving attendance");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <ListCard dark title="Update Attendance">
      <ClassPicker picker={picker} value={sel} onChange={onPick} />

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

          {students && (
            <>
              <hr />
              <div className="form-group">
                <label>Student Attendance</label>
                <div className="list-group student-attendance-list">
                  {students.map((s) => (
                    <div
                      key={s.id}
                      className="list-group-item d-flex justify-content-between align-items-center flex-wrap"
                    >
                      <span className="student-name">
                        {s.roll_number && <span className="student-roll">{s.roll_number}</span>}
                        {s.name}
                      </span>
                      <StatusButtons
                        value={statuses[s.id]}
                        onChange={(val) => setStatuses((m) => ({ ...m, [s.id]: val }))}
                      />
                    </div>
                  ))}
                </div>
              </div>
              <div className="form-group mt-3">
                <button type="button" className="btn btn-success" onClick={save} disabled={saving}>
                  {saving ? "Updating Attendance Data..." : "Save Attendance"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </ListCard>
  );
}

export default StaffUpdateAttendance;
