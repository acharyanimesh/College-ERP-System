import { useState } from "react";
import notificationAPI from "../../../api/notifications";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";
import NotificationModal from "./NotificationModal";

/** Send Notifications To Staff (hod_template/staff_notification.html). */
function NotifyStaff() {
  usePageHeader({
    title: "Send Notifications To Staff",
    breadcrumb: [{ text: "Notify Staff" }],
  });
  const { data: allStaff } = useApi(() => notificationAPI.getStaffRecipients());
  const [targetId, setTargetId] = useState(null);

  return (
    <ListCard title="Send Notifications To Staff">
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Full Name</th>
            <th>Email</th>
            <th>Gender</th>
            <th>Avatar</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {allStaff?.map((staff, i) => (
            <tr key={staff.id}>
              <td>{i + 1}</td>
              <td>
                {staff.first_name} {staff.last_name}
              </td>
              <td>{staff.email}</td>
              <td>{staff.gender}</td>
              <td>
                {staff.profile_pic ? (
                  <img
                    className="img img-fluid mb-2"
                    height={56}
                    width={56}
                    src={staff.profile_pic}
                    alt=""
                  />
                ) : (
                  "No Image"
                )}
              </td>
              <td>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setTargetId(staff.id)}
                >
                  Send Notification
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <NotificationModal
        show={targetId !== null}
        onClose={() => setTargetId(null)}
        onSend={(message) => notificationAPI.sendToStaff(targetId, message)}
      />
    </ListCard>
  );
}

export default NotifyStaff;
