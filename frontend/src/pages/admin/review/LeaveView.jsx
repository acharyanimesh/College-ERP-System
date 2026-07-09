import { useState } from "react";
import leaveAPI from "../../../api/leave";
import { ListCard } from "../../../components/ListCard";
import Modal from "../../../components/Modal";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/**
 * Admin leave review for staff or students
 * (staff_leave_view.html / student_leave_view.html): pending rows get a
 * Reply button opening the approve/reject modal.
 */
function LeaveView({ role }) {
  const isStaff = role === "staff";
  const pageTitle = isStaff
    ? "Leave Applications From Staff"
    : "Leave Applications From Students";
  usePageHeader({ title: pageTitle, breadcrumb: [{ text: pageTitle }] });

  const { data: allLeave, reload } = useApi(() => leaveAPI.getAll(role), [role]);
  const [target, setTarget] = useState(null); // { id, name }
  const [status, setStatus] = useState("");

  const submit = async () => {
    if (status !== "1" && status !== "-1") {
      window.alert("Choose valid response");
      return;
    }
    try {
      await leaveAPI.setStatus(role, target.id, Number(status));
      window.alert("Leave Response Has Been Saved!");
      setTarget(null);
      setStatus("");
      reload();
    } catch {
      window.alert("Reply Could Not Be Sent");
    }
  };

  return (
    <ListCard dark title={pageTitle} scrollBody>
      <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
        <tbody>
          <tr>
            <th>#</th>
            <th>{isStaff ? "Staff" : "Student"}</th>
            <th>Course</th>
            <th>Message</th>
            <th>Leave Date</th>
            <th>Submitted On</th>
            <th>Action</th>
          </tr>
          {allLeave?.map((leave, i) => (
            <tr key={leave.id}>
              <td>{i + 1}</td>
              <td>{leave.person_name}</td>
              <td>
                {leave.course_names || <span className="text-muted">—</span>}
              </td>
              <td
                style={{
                  wordWrap: "break-word",
                  maxWidth: 200,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {leave.message}
              </td>
              <td>{leave.date}</td>
              <td>{leave.created_at}</td>
              <td>
                {leave.status === 0 ? (
                  <button
                    type="button"
                    className="btn btn-success"
                    onClick={() => {
                      setTarget({ id: leave.id, name: leave.person_name });
                      setStatus("");
                    }}
                  >
                    Reply
                  </button>
                ) : leave.status === -1 ? (
                  <span className="badge badge-danger">Rejected</span>
                ) : (
                  <span className="badge badge-success">Approved</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Modal
        show={target !== null}
        onClose={() => setTarget(null)}
        header=""
        footer={
          <button type="button" className="btn btn-success" onClick={submit}>
            Submit
          </button>
        }
      >
        <p>
          Reply To <span>{target?.name}</span>'s Leave Request
        </p>
        <select
          className="form-control"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">-- Select --</option>
          <option value="1">Approve</option>
          <option value="-1">Reject</option>
        </select>
      </Modal>
    </ListCard>
  );
}

export default LeaveView;
