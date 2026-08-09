import { useEffect, useState } from "react";
import financeAPI from "../../api/finance";
import { rs } from "../../constants/money";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Fee Structure: the per-semester price list, one editable amount per course ×
 * semester. This is what makes every "outstanding" figure elsewhere mean
 * something — a student's term bill is read straight off this grid.
 */
function FeeStructures() {
  usePageHeader({
    title: "Fee Structure",
    breadcrumb: [{ text: "Fee Structure" }],
  });
  const { addMessage } = useMessages();
  // grid[courseId][semester] = amount (string while editing)
  const [grid, setGrid] = useState(null);
  const [courses, setCourses] = useState([]);
  const [saving, setSaving] = useState(false);

  const load = () => {
    financeAPI
      .getFeeStructures()
      .then((data) => {
        setCourses(data.courses);
        const g = {};
        data.courses.forEach((c) => {
          g[c.course_id] = {};
          c.semesters.forEach((s) => {
            g[c.course_id][s.semester] = String(s.amount || "");
          });
        });
        setGrid(g);
      })
      .catch(() => addMessage("Could not load the fee structure.", "danger"));
  };

  useEffect(load, [addMessage]);

  const setAmount = (courseId, semester, value) => {
    setGrid((g) => ({
      ...g,
      [courseId]: { ...g[courseId], [semester]: value },
    }));
  };

  const save = async () => {
    const items = [];
    courses.forEach((c) => {
      c.semesters.forEach((s) => {
        const raw = grid[c.course_id][s.semester];
        const amount = parseInt(raw, 10) || 0;
        items.push({ course: c.course_id, semester: s.semester, amount });
      });
    });
    setSaving(true);
    try {
      const result = await financeAPI.saveFeeStructures(items);
      addMessage(result.detail || "Fee structure saved.", "success");
      load();
    } catch {
      addMessage("Could not save the fee structure.", "danger");
    } finally {
      setSaving(false);
    }
  };

  const courseTotal = (c) =>
    c.semesters.reduce(
      (sum, s) => sum + (parseInt(grid?.[c.course_id]?.[s.semester], 10) || 0),
      0
    );

  if (!grid) return null;

  return (
    <section className="content">
      <div className="container-fluid">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <p className="text-muted mb-0">
            Set the tuition fee charged per semester for each course. Leave a
            semester at 0 if it isn't billed.
          </p>
          <button className="btn btn-success" onClick={save} disabled={saving}>
            <i className="fas fa-save me-2"></i>
            {saving ? "Saving…" : "Save All"}
          </button>
        </div>

        <div className="row">
          {courses.map((c) => (
            <div className="col-lg-6 mb-4" key={c.course_id}>
              <div className="card card-dark h-100">
                <div className="card-header d-flex justify-content-between align-items-center">
                  <h3 className="card-title">{c.course_name}</h3>
                  <span className="badge badge-info">{rs(courseTotal(c))} / degree</span>
                </div>
                <div className="card-body">
                  <table className="table table-sm table-borderless mb-0">
                    <tbody>
                      {c.semesters.map((s) => (
                        <tr key={s.semester}>
                          <td style={{ width: 140 }}>
                            <label className="mb-0" htmlFor={`fee_${c.course_id}_${s.semester}`}>
                              Semester {s.semester}
                            </label>
                          </td>
                          <td>
                            <div className="input-group input-group-sm">
                              <span className="input-group-text">Rs.</span>
                              <input
                                id={`fee_${c.course_id}_${s.semester}`}
                                type="number"
                                min="0"
                                className="form-control"
                                value={grid[c.course_id][s.semester]}
                                onChange={(e) =>
                                  setAmount(c.course_id, s.semester, e.target.value)
                                }
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                      {!c.semesters.length && (
                        <tr>
                          <td className="text-muted">
                            Set the number of semesters for this course first.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default FeeStructures;
