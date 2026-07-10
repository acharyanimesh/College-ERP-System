import { useEffect, useState } from "react";
import resultAPI from "../../api/results";
import { ListCard } from "../../components/ListCard";
import { FINAL_GRADE_OPTIONS } from "../../constants/grades";
import { usePageHeader, useMessages } from "../../layouts/Layout";
import { PICKER_STYLES } from "./ClassPicker";

const NUMERIC_FIELDS = ["unit_test", "internal", "pre_board"];

function isRowComplete(row) {
  return (
    NUMERIC_FIELDS.every((f) => row[f] !== null && row[f] !== "" && row[f] !== undefined) &&
    !!row.final_grade
  );
}

/**
 * Manage Result (merges the old Add Result / Edit Results pages): pick a
 * subject the teacher is assigned to, then a class (course + semester) they
 * teach it in — both shifts share one result set, so there's no shift step.
 * The roster loads in roll-number order with any existing marks prefilled;
 * Save upserts the whole table, View reloads the server's saved state
 * read-only, and Finalize locks the set once every student is complete.
 */
function StaffManageResult() {
  usePageHeader({ title: "Manage Result", breadcrumb: [{ text: "Manage Result" }] });
  const { addMessage } = useMessages();

  const [subjects, setSubjects] = useState([]);
  const [subject, setSubject] = useState("");
  const [classSel, setClassSel] = useState(""); // "course|semester"
  const [rows, setRows] = useState(null);
  const [finalized, setFinalized] = useState(false);
  const [viewMode, setViewMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    resultAPI.getClasses().then((data) => setSubjects(data.subjects || [])).catch(() => {});
  }, []);

  const subjectObj = subjects.find((s) => String(s.id) === String(subject));
  const classes = subjectObj?.classes || [];
  const [course, semester] = classSel ? classSel.split("|") : [null, null];

  const pickSubject = (id) => {
    setSubject(id);
    setClassSel("");
    setRows(null);
    setViewMode(false);
  };

  const loadClass = async (courseId, semesterVal) => {
    setLoading(true);
    try {
      const data = await resultAPI.getClassResults({
        subject, course: courseId, semester: semesterVal,
      });
      setRows(data.rows);
      setFinalized(data.finalized);
      return true;
    } catch {
      addMessage("Could not load students for this class.", "danger");
      return false;
    } finally {
      setLoading(false);
    }
  };

  const pickClass = async (value) => {
    setClassSel(value);
    setRows(null);
    setViewMode(false);
    if (!value) return;
    const [c, s] = value.split("|");
    await loadClass(c, s);
  };

  const toggleView = async () => {
    if (!viewMode) {
      const ok = await loadClass(course, semester);
      if (!ok) return;
    }
    setViewMode((v) => !v);
  };

  const setCell = (studentId, field, value) => {
    setRows((rs) => rs.map((r) => (r.student === studentId ? { ...r, [field]: value } : r)));
  };

  const allComplete = !!rows && rows.length > 0 && rows.every(isRowComplete);

  const save = async () => {
    setSaving(true);
    try {
      await resultAPI.saveClassResults({ subject, course, semester, rows });
      addMessage("Results saved", "success");
    } catch {
      addMessage("Could not save results.", "danger");
    } finally {
      setSaving(false);
    }
  };

  const doFinalize = async () => {
    if (!window.confirm(
      "Finalize this result? Once finalized, marks can no longer be edited."
    )) {
      return;
    }
    setFinalizing(true);
    try {
      await resultAPI.finalize({ subject, course, semester });
      setFinalized(true);
      addMessage("Result finalized", "success");
    } catch (err) {
      const code = err.response?.data?.code;
      if (code === "INCOMPLETE") {
        addMessage(
          "Enter all marks and the final grade for every student before finalizing.",
          "warning"
        );
      } else {
        addMessage("Could not finalize result.", "danger");
      }
    } finally {
      setFinalizing(false);
    }
  };

  const readOnly = finalized || viewMode;

  return (
    <ListCard dark title="Manage Result">
      <style>{PICKER_STYLES}</style>

      <div className="form-group">
        <label>Subject</label>
        <div className="subject-picker">
          {subjects.length === 0 && (
            <span className="text-muted">You are not assigned to any subjects.</span>
          )}
          {subjects.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`btn btn-outline-primary subject-btn ${
                String(subject) === String(s.id) ? "active" : ""
              }`}
              onClick={() => pickSubject(s.id)}
            >
              {s.name}
            </button>
          ))}
        </div>
        <small className="text-muted">
          Click a subject you teach.
        </small>
      </div>

      {subject && (
        <div className="form-group">
          <label>Class (Course &amp; Semester)</label>
          <select
            className="form-control"
            value={classSel}
            onChange={(e) => pickClass(e.target.value)}
          >
            <option value="">----</option>
            {classes.map((c) => (
              <option key={`${c.course}|${c.semester}`} value={`${c.course}|${c.semester}`}>
                {c.course_name} — Semester {c.semester}
              </option>
            ))}
          </select>
          <small className="text-muted">
            Results cover both shifts together — students are listed by roll number.
          </small>
        </div>
      )}

      {loading && <p className="text-muted">Loading students...</p>}

      {rows && (
        <div className="form-group">
          <hr />
          {finalized && (
            <div className="alert alert-success">
              <i className="fas fa-lock"></i> This result has been finalized and can no
              longer be edited.
            </div>
          )}
          <div className="d-flex justify-content-between align-items-center mb-2">
            <label className="mb-0">Student Results</label>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={toggleView}
              disabled={finalized}
            >
              <i className={`fas fa-${viewMode ? "pencil-alt" : "eye"}`}></i>{" "}
              {viewMode ? "Edit" : "View"}
            </button>
          </div>
          <div className="table-responsive student-attendance-table">
            <table className="table">
              <thead>
                <tr>
                  <th>Roll No.</th>
                  <th>Name</th>
                  <th>Unit Test</th>
                  <th>Internal</th>
                  <th>Pre-board</th>
                  <th>Final Grade</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.student}>
                    <td className="student-roll">{r.roll_number || "—"}</td>
                    <td className="student-name">{r.name}</td>
                    {NUMERIC_FIELDS.map((field) =>
                      readOnly ? (
                        <td key={field}>{r[field] ?? "—"}</td>
                      ) : (
                        <td key={field}>
                          <input
                            type="number"
                            className="form-control form-control-sm"
                            min={0}
                            max={100}
                            value={r[field] ?? ""}
                            onChange={(e) =>
                              setCell(
                                r.student,
                                field,
                                e.target.value === "" ? null : e.target.value
                              )
                            }
                          />
                        </td>
                      )
                    )}
                    <td>
                      {readOnly ? (
                        r.final_grade || "—"
                      ) : (
                        <select
                          className="form-control form-control-sm"
                          value={r.final_grade || ""}
                          onChange={(e) => setCell(r.student, "final_grade", e.target.value)}
                        >
                          <option value="">--</option>
                          {FINAL_GRADE_OPTIONS.map((g) => (
                            <option key={g} value={g}>
                              {g}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!readOnly && (
            <div className="d-flex gap-2 mt-3">
              <button
                type="button"
                className="btn btn-success"
                onClick={save}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Results"}
              </button>
              <button
                type="button"
                className="btn btn-warning"
                onClick={doFinalize}
                disabled={finalizing || !allComplete}
                title={
                  !allComplete
                    ? "Enter all marks and grades for every student first"
                    : undefined
                }
              >
                {finalizing ? "Finalizing..." : "Finalize Result"}
              </button>
            </div>
          )}
        </div>
      )}
    </ListCard>
  );
}

export default StaffManageResult;
