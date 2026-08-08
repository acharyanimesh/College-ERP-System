import { useState } from "react";
import libraryAPI from "../../api/library";
import { ListCard } from "../../components/ListCard";
import Modal from "../../components/Modal";
import useApi from "../../hooks/useApi";
import { usePageHeader, useMessages } from "../../layouts/Layout";

// Widest first, narrowing to the one thing that needs a decision: All →
// Borrowed → Ready for pickup → Pending. Pending stays the tab the page
// opens on (see useState below) — it is the working queue, wherever it sits.
const TABS = [
  { key: "", label: "All", icon: "fas fa-list" },
  { key: "issued", label: "Borrowed", icon: "fas fa-book-reader" },
  { key: "approved", label: "Ready for pickup", icon: "fas fa-check" },
  { key: "pending", label: "Pending", icon: "fas fa-hourglass-half" },
];

const STATUS_BADGE = {
  pending: "badge-warning",
  approved: "badge-info",
  issued: "badge-success",
  returned: "badge-secondary",
  rejected: "badge-danger",
  cancelled: "badge-secondary",
};

/**
 * Borrow Requests — the librarian's queue. Pending rows get Approve/Reject;
 * approved ones wait for the student to turn up and are then marked
 * collected; borrowed ones come back here to be returned.
 */
function BorrowRequests() {
  usePageHeader({
    title: "Borrow Requests",
    breadcrumb: [{ text: "Circulation" }, { text: "Borrow Requests" }],
  });
  const { addMessage } = useMessages();

  const [tab, setTab] = useState("pending");
  const [query, setQuery] = useState("");
  const { data: requests, reload } = useApi(
    () => libraryAPI.getRequests({ status: tab || undefined, q: query || undefined }),
    [tab, query]
  );

  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");
  const [busyId, setBusyId] = useState(null);

  const run = async (req, action, fn) => {
    setBusyId(req.id);
    try {
      await fn();
      addMessage(`"${req.book_name}" — ${action}.`, "success");
      reload();
    } catch (err) {
      addMessage(err.response?.data?.detail || `Could not ${action}.`, "danger");
    } finally {
      setBusyId(null);
    }
  };

  const approve = (req) =>
    run(req, "approved", () => libraryAPI.approve(req.id));
  const issue = (req) =>
    run(req, "handed over", () => libraryAPI.issue(req.id));
  const markReturned = (req) =>
    run(req, "returned", () => libraryAPI.markReturned(req.id));

  const submitRejection = async () => {
    if (!reason.trim()) {
      addMessage("Please give the student a reason.", "danger");
      return;
    }
    const req = rejecting;
    setRejecting(null);
    await run(req, "declined", () => libraryAPI.reject(req.id, reason));
    setReason("");
  };

  const actionsFor = (req) => {
    const busy = busyId === req.id;
    if (req.status === "pending") {
      const noCopies = req.available_copies < 1;
      return (
        <>
          <button
            type="button"
            className="btn btn-sm btn-success"
            disabled={busy || noCopies}
            title={
              noCopies
                ? "Every copy is out — nothing to hand over yet"
                : "Approve this request"
            }
            onClick={() => approve(req)}
          >
            <i className="fas fa-check"></i> Approve
          </button>{" "}
          <button
            type="button"
            className="btn btn-sm btn-danger"
            disabled={busy}
            onClick={() => {
              setRejecting(req);
              setReason("");
            }}
          >
            <i className="fas fa-times"></i> Reject
          </button>
        </>
      );
    }
    if (req.status === "approved") {
      return (
        <>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={busy}
            onClick={() => issue(req)}
          >
            <i className="fas fa-hand-holding"></i> Mark collected
          </button>{" "}
          <button
            type="button"
            className="btn btn-sm btn-outline-danger"
            disabled={busy}
            title="The student never came for it"
            onClick={() => {
              setRejecting(req);
              setReason("Not collected");
            }}
          >
            Lapsed
          </button>
        </>
      );
    }
    if (req.status === "issued") {
      return (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          disabled={busy}
          onClick={() => markReturned(req)}
        >
          <i className="fas fa-undo"></i> Mark returned
        </button>
      );
    }
    return <span className="text-muted">—</span>;
  };

  return (
    <ListCard title="Borrow Requests" scrollBody>
      <div className="d-flex flex-wrap justify-content-between align-items-center mb-3">
        <div className="btn-group">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              className={`btn btn-sm ${
                tab === t.key ? "btn-primary" : "btn-outline-primary"
              }`}
              onClick={() => setTab(t.key)}
            >
              <i className={t.icon}></i> {t.label}
            </button>
          ))}
        </div>
        <input
          type="text"
          className="form-control"
          style={{ maxWidth: 320 }}
          placeholder="Search by book, student name or roll..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <table className="table table-bordered table-hover" style={{ minWidth: 1000 }}>
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Student</th>
            <th>Book</th>
            <th>Requested</th>
            <th>Status</th>
            <th>Stock</th>
            <th>Due / Fine</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {!requests?.length && (
            <tr>
              <td colSpan={8} className="text-center">
                Nothing here right now.
              </td>
            </tr>
          )}
          {requests?.map((req, i) => (
            <tr key={req.id}>
              <td>{i + 1}</td>
              <td>
                {req.student_name}
                <br />
                <small className="text-muted">
                  {req.student_roll || "—"} · {req.student_course} · Sem{" "}
                  {req.student_semester}
                </small>
              </td>
              <td>
                {req.book_name}
                <br />
                <small className="text-muted">
                  {req.book_author} · {req.book_isbn}
                </small>
                {req.student_note && (
                  <>
                    <br />
                    <small className="font-italic">"{req.student_note}"</small>
                  </>
                )}
              </td>
              <td>{req.requested_at}</td>
              <td>
                <span className={`badge ${STATUS_BADGE[req.status]}`}>
                  {req.status_display}
                </span>
                {req.librarian_note && (
                  <>
                    <br />
                    <small className="text-muted">{req.librarian_note}</small>
                  </>
                )}
              </td>
              <td>
                <span
                  className={`badge ${
                    req.available_copies ? "badge-success" : "badge-secondary"
                  }`}
                >
                  {req.available_copies} free
                </span>
              </td>
              <td>
                {req.due_date || <span className="text-muted">—</span>}
                {req.days_overdue > 0 && (
                  <>
                    <br />
                    <small className="text-danger">
                      {req.days_overdue}d late · Rs. {req.fine}
                    </small>
                  </>
                )}
              </td>
              <td className="text-nowrap">{actionsFor(req)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <Modal
        show={rejecting !== null}
        onClose={() => setRejecting(null)}
        header={<h5 className="modal-title">Decline request</h5>}
        footer={
          <button
            type="button"
            className="btn btn-danger"
            onClick={submitRejection}
          >
            Decline and notify
          </button>
        }
      >
        <p>
          Declining <strong>{rejecting?.book_name}</strong> for{" "}
          {rejecting?.student_name}.
        </p>
        <div className="form-group">
          <label htmlFor="reject-reason">Reason (the student is shown this)</label>
          <textarea
            id="reject-reason"
            className="form-control"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. reserved for the reference section"
          />
        </div>
      </Modal>
    </ListCard>
  );
}

export default BorrowRequests;
