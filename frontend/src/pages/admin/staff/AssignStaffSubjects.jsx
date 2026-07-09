import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import staffAPI from "../../../api/staff";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/**
 * Assign Subjects to a staff member (assign_staff_subjects.html): one
 * checkbox per (course-subject, shift), slots held by another teacher are
 * locked and show their name.
 */
function AssignStaffSubjects() {
  const { staffId } = useParams();
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState({ morning: new Set(), day: new Set() });
  const [submitting, setSubmitting] = useState(false);

  const { data } = useApi(() => staffAPI.getSubjectAssignments(staffId), [staffId]);

  const title = data?.staff_name
    ? `Assign Subjects - ${data.staff_name}`
    : "Assign Subjects";
  usePageHeader({ title, breadcrumb: [{ text: "Assign Subjects" }] });

  // Seed the checkboxes from the currently-held slots.
  useEffect(() => {
    if (!data?.rows) return;
    setSelected({
      morning: new Set(
        data.rows.filter((r) => r.morning_mine).map((r) => r.cs_id)
      ),
      day: new Set(data.rows.filter((r) => r.day_mine).map((r) => r.cs_id)),
    });
  }, [data]);

  const rows = data?.rows;
  const visible = useMemo(() => {
    if (!rows) return [];
    const q = query.toLowerCase().trim();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        `${r.subject_code || ""} ${r.subject_name}`.toLowerCase().includes(q) ||
        (r.course_short_name || "").toLowerCase().includes(q)
    );
  }, [rows, query]);

  const toggle = (shift, csId) => {
    setSelected((prev) => {
      const next = new Set(prev[shift]);
      if (next.has(csId)) next.delete(csId);
      else next.add(csId);
      return { ...prev, [shift]: next };
    });
  };

  const save = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await staffAPI.saveSubjectAssignments(staffId, {
        morning: [...selected.morning],
        day: [...selected.day],
      });
      addMessage("Assignments saved.", "success");
      navigate("/staff/manage/");
    } catch {
      addMessage("Could not save the assignments.", "danger");
      setSubmitting(false);
    }
  };

  const shiftCell = (row, shift) => {
    const other = row[`${shift}_other`];
    if (other) {
      return (
        <span className="badge badge-warning" style={{ fontSize: "0.82rem" }} title="Taken">
          {other}
        </span>
      );
    }
    return (
      <input
        type="checkbox"
        style={{ transform: "scale(1.25)", cursor: "pointer" }}
        checked={selected[shift].has(row.cs_id)}
        onChange={() => toggle(shift, row.cs_id)}
      />
    );
  };

  return (
    <form onSubmit={save}>
      <ListCard
        dark
        title={title}
        action={<BackButton to="/staff/manage/">Back to Manage Staff</BackButton>}
      >
        <p className="text-muted">
          Tick the shift(s) this teacher takes for each subject. Only{" "}
          <strong>one teacher per subject per shift</strong> is allowed — a
          slot already held by another teacher is locked and shows their name.
          The same teacher may teach across multiple courses, subjects and
          shifts.
        </p>
        <div className="form-group" style={{ maxWidth: 360 }}>
          <input
            type="text"
            className="form-control"
            placeholder="Search by subject or course..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div style={{ overflowX: "auto", maxHeight: 600 }}>
          <table
            className="table table-bordered table-hover"
            style={{ minWidth: 760, verticalAlign: "middle" }}
          >
            <thead className="thead-dark">
              <tr>
                <th>#</th>
                <th>Subject</th>
                <th>Course</th>
                <th>Sem</th>
                <th className="text-center text-nowrap">Morning</th>
                <th className="text-center text-nowrap">Day</th>
              </tr>
            </thead>
            <tbody>
              {rows && !rows.length && (
                <tr>
                  <td colSpan={6} className="text-center">
                    No course subjects available. Add subjects to courses first.
                  </td>
                </tr>
              )}
              {rows?.length > 0 && !visible.length && (
                <tr>
                  <td colSpan={6} className="text-center">
                    No rows match your search.
                  </td>
                </tr>
              )}
              {visible.map((row, i) => (
                <tr key={row.cs_id}>
                  <td>{i + 1}</td>
                  <td>
                    {row.subject_code && <strong>{row.subject_code}</strong>}
                    {row.subject_code && " — "}
                    {row.subject_name}
                  </td>
                  <td title={row.course_name}>{row.course_short_name}</td>
                  <td>{row.semester || "?"}</td>
                  <td className="text-center text-nowrap">{shiftCell(row, "morning")}</td>
                  <td className="text-center text-nowrap">{shiftCell(row, "day")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="submit" className="btn btn-success btn-block w-100" disabled={submitting}>
          Save Assignments
        </button>
      </ListCard>
    </form>
  );
}

export default AssignStaffSubjects;
