import { useState } from "react";
import attendanceAPI from "../../api/attendance";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";
import ClassPicker from "./ClassPicker";

function todayStr() {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(
    t.getDate()
  ).padStart(2, "0")}`;
}

/** Present/Absent/Late toggle row used by Take and Update attendance. */
export function StatusButtons({ value, onChange }) {
  return (
    <div className="btn-group attendance-status" role="group">
      {[
        ["present", "btn-outline-success", "Present"],
        ["absent", "btn-outline-danger", "Absent"],
        ["late", "btn-outline-warning", "Late"],
      ].map(([val, cls, label]) => (
        <button
          key={val}
          type="button"
          className={`btn ${cls} status-btn ${value === val ? "active" : ""}`}
          onClick={() => onChange(val)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/** Status → { status, late } codes save_attendance expects. */
export function statusPayload(students, statuses) {
  return students.map((s) => {
    const val = statuses[s.id];
    return { id: s.id, status: val === "absent" ? 0 : 1, late: val === "late" ? 1 : 0 };
  });
}

/** Take Attendance (staff_template/staff_take_attendance.html). */
function StaffTakeAttendance() {
  usePageHeader({
    title: "Take Attendance",
    breadcrumb: [{ text: "Take Attendance" }],
  });
  const { data: picker } = useApi(() => attendanceAPI.getPicker());

  const [sel, setSel] = useState({ shift: "morning", subject: "", course: "", semester: "" });
  const [students, setStudents] = useState(null);
  const [statuses, setStatuses] = useState({});
  const [date, setDate] = useState(todayStr());
  const [saving, setSaving] = useState(false);

  const onPick = (patch) => {
    setSel((s) => ({ ...s, ...patch }));
    setStudents(null);
  };

  const fetchStudents = async () => {
    const { subject, course, semester, shift } = sel;
    if (!subject || !course || !semester || !shift) {
      window.alert("Please select subject, course, semester and shift");
      return;
    }
    try {
      const data = await attendanceAPI.getStudents({ course, semester, shift });
      if (!data.length) {
        window.alert("No data to display");
        setStudents(null);
        return;
      }
      setStudents(data);
      setStatuses({});
      setDate(todayStr());
    } catch {
      window.alert("Error in fetching students");
    }
  };

  const save = async () => {
    // Nothing is preselected, so make sure every student has been marked.
    const unmarked = students.filter((s) => !statuses[s.id]).length;
    if (unmarked > 0) {
      window.alert(
        `Please mark Present, Absent or Late for all ${unmarked} remaining student(s) before saving.`
      );
      return;
    }
    setSaving(true);
    try {
      await attendanceAPI.save({
        date,
        student_ids: statusPayload(students, statuses),
        subject: sel.subject,
        course: sel.course,
        semester: sel.semester,
        shift: sel.shift,
      });
      window.alert("Saved");
      setStudents(null);
    } catch (err) {
      const code = err.response?.data?.code;
      if (code === "NOT_ASSIGNED") {
        window.alert(
          "You are not assigned to this subject at the selected course/semester/shift, so you cannot take its attendance."
        );
      } else if (code === "NO_SESSION") {
        window.alert(
          "These students have no session/intake set, so attendance cannot be recorded. Please set their session first."
        );
      } else if (code === "ALREADY_CONFIRMED") {
        window.alert(
          "Attendance for this subject/shift on this date has already been confirmed and cannot be taken again."
        );
        setStudents(null);
      } else if (code === "ALREADY_TAKEN") {
        window.alert(
          "Attendance for this subject/shift on this date has already been saved. Use Update Attendance to edit or confirm it instead of taking it again."
        );
        setStudents(null);
      } else {
        window.alert("Error in saving attendance");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <ListCard dark title="Take Attendance">
      <ClassPicker picker={picker} value={sel} onChange={onPick} />

      <button type="button" className="btn btn-success btn-block w-100" onClick={fetchStudents}>
        Fetch Students
      </button>

      {students && (
        <div className="form-group">
          <hr />
          <div className="form-group">
            <label>Attendance Date</label>
            <input
              type="date"
              className="form-control attendance-date-input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
            <small className="text-muted">
              Select the date you are taking attendance for.
            </small>
          </div>
          <div className="table-responsive student-attendance-table">
            <table className="table">
              <thead>
                <tr>
                  <th>Roll No.</th>
                  <th>Name</th>
                  <th className="text-end">Status</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id}>
                    <td className="student-roll">{s.roll_number || "—"}</td>
                    <td className="student-name">{s.name}</td>
                    <td className="text-end">
                      <StatusButtons
                        value={statuses[s.id]}
                        onChange={(val) => setStatuses((m) => ({ ...m, [s.id]: val }))}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="form-group mt-3">
            <button type="button" className="btn btn-success" onClick={save} disabled={saving}>
              {saving ? "Saving Attendance Data..." : "Save Attendance"}
            </button>
          </div>
        </div>
      )}
    </ListCard>
  );
}

export default StaffTakeAttendance;
