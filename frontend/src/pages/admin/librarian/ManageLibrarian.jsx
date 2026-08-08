import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import librarianAPI from "../../../api/librarians";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Manage Librarians table — the librarian counterpart of ManageStaff. */
function ManageLibrarian() {
  usePageHeader({
    title: "Manage Librarians",
    breadcrumb: [{ text: "Manage Librarians" }],
  });
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");

  const { data: allLibrarians, reload } = useApi(() => librarianAPI.getAll());

  const visible = useMemo(() => {
    if (!allLibrarians) return [];
    const q = query.toLowerCase().trim();
    if (!q) return allLibrarians;
    return allLibrarians.filter(
      (l) =>
        (l.librarian_id || "").toLowerCase().includes(q) ||
        `${l.first_name} ${l.last_name}`.toLowerCase().includes(q)
    );
  }, [allLibrarians, query]);

  const remove = async (librarian) => {
    if (!window.confirm("Are you sure about this ?")) return;
    try {
      await librarianAPI.delete(librarian.id);
      addMessage("Librarian deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Could not delete the librarian.", "danger");
    }
  };

  const resend = async (librarian) => {
    try {
      await librarianAPI.resendVerification(librarian.id);
      addMessage("Verification email sent.", "success");
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not send the verification email.",
        "danger"
      );
    }
  };

  return (
    <ListCard title="Manage Librarians" scrollBody>
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by librarian ID or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Librarian ID</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {!allLibrarians?.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No librarian accounts yet.{" "}
                <Link to="/librarian/add">Add one</Link>.
              </td>
            </tr>
          )}
          {allLibrarians?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No librarians match your search.
              </td>
            </tr>
          )}
          {visible.map((l, i) => (
            <tr
              key={l.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/librarian/details/${l.id}`)}
            >
              <td>{i + 1}</td>
              <td>{l.librarian_id || "—"}</td>
              <td>
                {l.first_name} {l.last_name}
              </td>
              <td>{l.email}</td>
              <td>
                {l.verified ? (
                  <span className="badge badge-success">Verified</span>
                ) : (
                  <span className="badge badge-warning">Pending verification</span>
                )}
              </td>
              <td className="text-nowrap" onClick={(e) => e.stopPropagation()}>
                {!l.verified && (
                  <>
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      title="Resend verification email"
                      onClick={() => resend(l)}
                    >
                      <i className="fas fa-paper-plane"></i>
                    </button>{" "}
                  </>
                )}
                <Link
                  to={`/librarian/edit/${l.id}`}
                  className="btn btn-sm btn-info"
                  title="Edit"
                >
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(l)}
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

export default ManageLibrarian;
