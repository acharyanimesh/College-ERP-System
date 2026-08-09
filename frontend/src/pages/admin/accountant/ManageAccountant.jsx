import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import accountantAPI from "../../../api/accountants";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Manage Accountants table — the accountant counterpart of ManageLibrarian. */
function ManageAccountant() {
  usePageHeader({
    title: "Manage Accountants",
    breadcrumb: [{ text: "Manage Accountants" }],
  });
  const navigate = useNavigate();
  const { addMessage } = useMessages();
  const [query, setQuery] = useState("");

  const { data: allAccountants, reload } = useApi(() => accountantAPI.getAll());

  const visible = useMemo(() => {
    if (!allAccountants) return [];
    const q = query.toLowerCase().trim();
    if (!q) return allAccountants;
    return allAccountants.filter(
      (a) =>
        (a.accountant_id || "").toLowerCase().includes(q) ||
        `${a.first_name} ${a.last_name}`.toLowerCase().includes(q)
    );
  }, [allAccountants, query]);

  const remove = async (accountant) => {
    if (!window.confirm("Are you sure about this ?")) return;
    try {
      await accountantAPI.delete(accountant.id);
      addMessage("Accountant deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Could not delete the accountant.", "danger");
    }
  };

  const resend = async (accountant) => {
    try {
      await accountantAPI.resendVerification(accountant.id);
      addMessage("Verification email sent.", "success");
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not send the verification email.",
        "danger"
      );
    }
  };

  return (
    <ListCard title="Manage Accountants" scrollBody>
      <div className="form-group" style={{ maxWidth: 360 }}>
        <input
          type="text"
          className="form-control"
          placeholder="Search by accountant ID or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Accountant ID</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {!allAccountants?.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No accountant accounts yet.{" "}
                <Link to="/accountant/add">Add one</Link>.
              </td>
            </tr>
          )}
          {allAccountants?.length > 0 && !visible.length && (
            <tr>
              <td colSpan={6} className="text-center">
                No accountants match your search.
              </td>
            </tr>
          )}
          {visible.map((a, i) => (
            <tr
              key={a.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/accountant/details/${a.id}`)}
            >
              <td>{i + 1}</td>
              <td>{a.accountant_id || "—"}</td>
              <td>
                {a.first_name} {a.last_name}
              </td>
              <td>{a.email}</td>
              <td>
                {a.verified ? (
                  <span className="badge badge-success">Verified</span>
                ) : (
                  <span className="badge badge-warning">Pending verification</span>
                )}
              </td>
              <td className="text-nowrap" onClick={(e) => e.stopPropagation()}>
                {!a.verified && (
                  <>
                    <button
                      type="button"
                      className="btn btn-sm btn-secondary"
                      title="Resend verification email"
                      onClick={() => resend(a)}
                    >
                      <i className="fas fa-paper-plane"></i>
                    </button>{" "}
                  </>
                )}
                <Link
                  to={`/accountant/edit/${a.id}`}
                  className="btn btn-sm btn-info"
                  title="Edit"
                >
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(a)}
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

export default ManageAccountant;
