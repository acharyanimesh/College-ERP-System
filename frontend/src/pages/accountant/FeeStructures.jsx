import { useState } from "react";
import { Link } from "react-router-dom";
import { courseAPI, sessionAPI } from "../../api/academics";
import feeAPI from "../../api/fees";
import Modal from "../../components/Modal";
import { ListCard } from "../../components/ListCard";
import { formatMoney } from "../../constants/money";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

/**
 * Every fee structure the college has written, with the clone action that
 * saves retyping eight heads for six courses each intake — retyping being
 * where the amounts drift.
 */
function FeeStructures() {
  usePageHeader({
    title: "Fee Structures",
    breadcrumb: [{ text: "Fee Structures" }],
  });
  const { addMessage } = useMessages();
  const [filters, setFilters] = useState({ course: "", session: "" });

  const { data: structures, reload } = useApi(
    () =>
      feeAPI.getStructures({
        course: filters.course || undefined,
        session: filters.session || undefined,
      }),
    [filters.course, filters.session]
  );
  const { data: courses } = useApi(() => courseAPI.getAll());
  const { data: sessions } = useApi(() => sessionAPI.getAll());

  const [cloning, setCloning] = useState(null);
  const [cloneTarget, setCloneTarget] = useState({ session: "", semester: "" });

  const remove = async (structure) => {
    if (
      !window.confirm(
        `Delete the fee structure for ${structure.course_name}, Semester ${structure.semester}?`
      )
    )
      return;
    try {
      await feeAPI.deleteStructure(structure.id);
      addMessage("Fee structure deleted.", "success");
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not delete the fee structure.",
        "danger"
      );
    }
  };

  const doClone = async () => {
    if (!cloneTarget.session) {
      addMessage("Pick the session to copy it to.", "danger");
      return;
    }
    try {
      await feeAPI.cloneStructure(cloning.id, {
        session: cloneTarget.session,
        semester: cloneTarget.semester || undefined,
      });
      addMessage("Fee structure copied.", "success");
      setCloning(null);
      reload();
    } catch (err) {
      addMessage(
        err.response?.data?.detail || "Could not copy the fee structure.",
        "danger"
      );
    }
  };

  return (
    <>
      <ListCard
        title="Fee Structures"
        action={
          <Link to="/accountant/fees/structures/add" className="btn btn-primary btn-sm">
            <i className="fas fa-plus me-1"></i> New Structure
          </Link>
        }
        scrollBody
      >
        <div className="row">
          <div className="col-md-4 form-group">
            <select
              className="form-control"
              value={filters.course}
              onChange={(e) =>
                setFilters((f) => ({ ...f, course: e.target.value }))
              }
            >
              <option value="">All courses</option>
              {courses?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_with_abbr}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-4 form-group">
            <select
              className="form-control"
              value={filters.session}
              onChange={(e) =>
                setFilters((f) => ({ ...f, session: e.target.value }))
              }
            >
              <option value="">All sessions</option>
              {sessions?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label || `${s.start_year} to ${s.end_year}`}
                </option>
              ))}
            </select>
          </div>
        </div>

        <table className="table table-bordered table-hover" style={{ minWidth: 900 }}>
          <thead className="thead-dark">
            <tr>
              <th>Course</th>
              <th>Session</th>
              <th>Sem</th>
              <th>Heads</th>
              <th>Total</th>
              <th>Due after</th>
              <th>Late fine/day</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {!structures?.length && (
              <tr>
                <td colSpan={8} className="text-center">
                  No fee structures yet.{" "}
                  <Link to="/accountant/fees/structures/add">Write one</Link>{" "}
                  before running the billing.
                </td>
              </tr>
            )}
            {structures?.map((s) => (
              <tr key={s.id}>
                <td>{s.course_name}</td>
                <td>{s.session_name}</td>
                <td>{s.semester}</td>
                <td>
                  {s.items?.map((item) => (
                    <span key={item.id} className="badge badge-info mr-1">
                      {item.head_name} {formatMoney(item.amount)}
                    </span>
                  ))}
                </td>
                <td className="font-weight-bold">{formatMoney(s.total)}</td>
                <td>{s.due_days} days</td>
                <td>
                  {Number(s.late_fine_per_day)
                    ? formatMoney(s.late_fine_per_day)
                    : "—"}
                </td>
                <td className="text-nowrap">
                  <Link
                    to={`/accountant/fees/structures/edit/${s.id}`}
                    className="btn btn-sm btn-info"
                    title="Edit"
                  >
                    <i className="fas fa-edit"></i>
                  </Link>{" "}
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    title="Copy to another session"
                    onClick={() => {
                      setCloning(s);
                      setCloneTarget({ session: "", semester: s.semester });
                    }}
                  >
                    <i className="fas fa-copy"></i>
                  </button>{" "}
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

      <Modal
        show={!!cloning}
        onClose={() => setCloning(null)}
        header={<h5 className="modal-title">Copy Fee Structure</h5>}
        footer={
          <button type="button" className="btn btn-primary" onClick={doClone}>
            Copy
          </button>
        }
      >
        {cloning && (
          <>
            <p>
              Copying <strong>{cloning.course_name}</strong>, Semester{" "}
              {cloning.semester} ({formatMoney(cloning.total)}).
            </p>
            <div className="form-group">
              <label>Copy to session</label>
              <select
                className="form-control"
                value={cloneTarget.session}
                onChange={(e) =>
                  setCloneTarget((t) => ({ ...t, session: e.target.value }))
                }
              >
                <option value="">Select a session</option>
                {sessions?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label || `${s.start_year} to ${s.end_year}`}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Semester</label>
              <input
                type="number"
                min={1}
                className="form-control"
                value={cloneTarget.semester}
                onChange={(e) =>
                  setCloneTarget((t) => ({ ...t, semester: e.target.value }))
                }
              />
            </div>
          </>
        )}
      </Modal>
    </>
  );
}

export default FeeStructures;
