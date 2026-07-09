import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import staffAPI from "../../../api/staff";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Manage Staff table (hod_template/manage_staff.html). */
function ManageStaff() {
  usePageHeader({ title: "Manage Staff", breadcrumb: [{ text: "Manage Staff" }] });
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");

  const { data: allStaff, reload } = useApi(() => staffAPI.getAll());

  const visible = useMemo(() => {
    if (!allStaff) return [];
    const q = query.toLowerCase().trim();
    if (!q) return allStaff;
    return allStaff.filter(
      (s) =>
        (s.staff_id || "").toLowerCase().includes(q) ||
        `${s.first_name} ${s.last_name}`.toLowerCase().includes(q)
    );
  }, [allStaff, query]);

  const remove = async (staff) => {
    if (!window.confirm("Are you sure about this ?")) return;
    try {
      await staffAPI.delete(staff.id);
      addMessage("Staff deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Could not delete the staff member.", "danger");
    }
  };

  return (
    <ListCard title="Manage Staff" scrollBody>
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by staff ID or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Staff ID</th>
            <th>Full Name</th>
            <th>Email</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {allStaff?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={5} className="text-center">
                No staff match your search.
              </td>
            </tr>
          )}
          {visible.map((s, i) => (
            <tr
              key={s.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/staff/view/${s.id}`)}
            >
              <td>{i + 1}</td>
              <td>{s.staff_id || "—"}</td>
              <td>
                {s.first_name} {s.last_name}
              </td>
              <td>{s.email}</td>
              <td className="text-nowrap" onClick={(e) => e.stopPropagation()}>
                <Link
                  to={`/staff/assign-subjects/${s.id}`}
                  className="btn btn-sm btn-success"
                  title="Assign Subjects"
                >
                  <i className="fas fa-book"></i>
                </Link>{" "}
                <Link to={`/staff/edit/${s.id}`} className="btn btn-sm btn-info" title="Edit">
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(s)}
                >
                  <i className="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default ManageStaff;
