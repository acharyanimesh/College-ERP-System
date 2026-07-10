import { useEffect, useMemo } from "react";

/**
 * Shift → Subject → Class picker shared by Take/Update/View Attendance
 * (and the scoped styles those templates repeated inline). A subject taught
 * in two courses is never ambiguous: each class option carries
 * course + semester. `restrictActive` hides classes not currently running
 * (Take/Update); View keeps them, labelled "(inactive)".
 *
 * value: { shift, subject, course, semester } — onChange(patch) merges.
 */

export const PICKER_STYLES = `
  .attendance-date-input {
    max-width: 200px;
    font-size: 0.95rem;
    height: auto;
    padding: 0.4rem 0.6rem;
  }
  .attendance-date-input::-webkit-calendar-picker-indicator {
    transform: scale(1.25);
    cursor: pointer;
    margin-left: 0.35rem;
    filter: invert(0.85);
  }
  .student-attendance-table th,
  .student-attendance-table td {
    vertical-align: middle;
  }
  .student-attendance-table .student-roll {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    white-space: nowrap;
  }
  .student-attendance-table .student-name {
    font-weight: 600;
  }
  .student-attendance-table .attendance-status .status-btn { min-width: 90px; }
  .student-attendance-table .status-badge {
    min-width: 90px;
    text-align: center;
    font-size: 0.85rem;
    padding: 0.45rem 0.75rem;
  }
  .subject-picker { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .subject-picker .subject-btn {
    font-weight: 500;
    border-radius: 6px;
    padding: 0.45rem 1rem;
  }
  .subject-picker .subject-btn.active {
    background: var(--primary-color, #5e64ff);
    border-color: var(--primary-color, #5e64ff);
    color: #fff;
    box-shadow: 0 2px 8px rgba(94, 100, 255, 0.35);
  }
`;

function ClassPicker({ picker, value, onChange, restrictActive = true, classHelp }) {
  const { shift, subject } = value;

  // Subjects this teacher takes in the selected shift.
  const visibleSubjects = useMemo(
    () => (picker?.subjects || []).filter((s) => s[shift]),
    [picker, shift]
  );

  // Clear a now-invalid subject selection when the shift changes.
  useEffect(() => {
    if (subject && !visibleSubjects.some((s) => String(s.id) === String(subject))) {
      onChange({ subject: "", course: "", semester: "" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleSubjects, subject]);

  const classes = useMemo(() => {
    const sel = (picker?.subjects || []).find((s) => String(s.id) === String(subject));
    if (!sel) return [];
    return (sel.classes || []).filter(
      (c) =>
        c.shift === shift &&
        c.semester != null &&
        (!restrictActive || c.active)
    );
  }, [picker, subject, shift, restrictActive]);

  const classValue = value.course && value.semester ? `${value.course}|${value.semester}` : "";

  return (
    <>
      <style>{PICKER_STYLES}</style>
      <div className="form-group">
        <label>Shift</label>
        <select
          className="form-control"
          value={shift}
          onChange={(e) => onChange({ shift: e.target.value, course: "", semester: "" })}
        >
          {picker?.shifts?.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Subject</label>
        <div className="subject-picker">
          {picker && !picker.subjects?.length && (
            <span className="text-muted">You are not assigned to any subjects.</span>
          )}
          {visibleSubjects.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`btn btn-outline-primary subject-btn ${
                String(subject) === String(s.id) ? "active" : ""
              }`}
              onClick={() => onChange({ subject: s.id, course: "", semester: "" })}
            >
              {s.name}
            </button>
          ))}
        </div>
        <small className="text-muted">
          Click a subject you teach. Only those valid for the selected shift are shown.
        </small>
      </div>

      <div className="form-group">
        <label>Class (Course &amp; Semester)</label>
        <select
          className="form-control"
          value={classValue}
          onChange={(e) => {
            const v = e.target.value;
            if (v.includes("|")) {
              const [course, semester] = v.split("|");
              onChange({ course, semester });
            } else {
              onChange({ course: "", semester: "" });
            }
          }}
        >
          {subject && !classes.length ? (
            <option value="">
              {restrictActive
                ? "No running classes for this subject/shift"
                : "No classes for this subject/shift"}
            </option>
          ) : (
            <option value="">----</option>
          )}
          {classes.map((c) => (
            <option key={`${c.course}|${c.semester}`} value={`${c.course}|${c.semester}`}>
              {c.course_name} — Semester {c.semester}
              {c.active ? "" : " (inactive)"}
            </option>
          ))}
        </select>
        <small className="text-muted">
          {classHelp ||
            "Pick a shift and subject first; only the classes currently running are listed."}
        </small>
      </div>
    </>
  );
}

export default ClassPicker;
