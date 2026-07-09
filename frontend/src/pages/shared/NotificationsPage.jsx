import notificationAPI from "../../api/notifications";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

/**
 * View Notifications, shared by staff and students
 * (staff_view_notification.html / student_view_notification.html).
 */
function NotificationsPage({ role }) {
  usePageHeader({
    title: "View Notifications",
    breadcrumb: [{ text: "View Notifications" }],
  });
  const { data: notifications } = useApi(() => notificationAPI.getMine(role), [role]);

  return (
    <ListCard dark title="View Notifications">
      <div className="form-group table">
        <table className="table table-bordered">
          <tbody>
            <tr>
              <th>#</th>
              <th>Date</th>
              <th>Message</th>
            </tr>
            {notifications?.map((n, i) => (
              <tr key={n.id}>
                <td>{i + 1}</td>
                <td>{n.created_at}</td>
                <td>{n.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ListCard>
  );
}

export default NotificationsPage;
