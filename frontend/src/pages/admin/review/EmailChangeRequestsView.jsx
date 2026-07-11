import emailChangeRequestsAPI from "../../../api/emailChangeRequests";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/**
 * Admin review queue for Staff/Student email-change requests
 * (ProfilePage.jsx's ChangeEmailCard submits these via
 * request_email_change). Approving sends the verification link to the new
 * address; rejecting drops the request with no email sent. Admin's own
 * email changes skip this entirely — see AdminEmailSetup.jsx.
 */
function EmailChangeRequestsView() {
  usePageHeader({
    title: "Email Change Requests",
    breadcrumb: [{ text: "Email Change Requests" }],
  });
  const { addMessage } = useMessages();
  const { data: requests, reload } = useApi(() => emailChangeRequestsAPI.getAll());

  const approve = async (req) => {
    try {
      await emailChangeRequestsAPI.approve(req.id);
      addMessage("Approved — verification email sent.", "success");
      reload();
    } catch (err) {
      addMessage(err.response?.data?.detail || "Could not approve this request.", "danger");
    }
  };

  const reject = async (req) => {
    if (!window.confirm(`Reject ${req.full_name}'s request to change their email?`)) return;
    try {
      await emailChangeRequestsAPI.reject(req.id);
      addMessage("Request rejected.", "success");
      reload();
    } catch {
      addMessage("Could not reject this request.", "danger");
    }
  };

  return (
    <ListCard dark title="Email Change Requests" scrollBody>
      <table className="table table-bordered table-hover" style={{ minWidth: 800 }}>
        <thead>
          <tr>
            <th>#</th>
            <th>Role</th>
            <th>Name</th>
            <th>Current Email</th>
            <th>Requested Email</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {requests?.length === 0 && (
            <tr>
              <td colSpan={6} className="text-center">
                No pending email change requests.
              </td>
            </tr>
          )}
          {requests?.map((req, i) => (
            <tr key={req.id}>
              <td>{i + 1}</td>
              <td>{req.role}</td>
              <td>{req.full_name}</td>
              <td>{req.email}</td>
              <td>{req.pending_email}</td>
              <td className="text-nowrap">
                <button
                  type="button"
                  className="btn btn-sm btn-success"
                  onClick={() => approve(req)}
                >
                  Approve
                </button>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  onClick={() => reject(req)}
                >
                  Reject
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default EmailChangeRequestsView;
