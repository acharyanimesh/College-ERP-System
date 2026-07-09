import axiosClient from "./axiosClient";

/** Notifications: admin sends, staff/students read their own. */
const notificationAPI = {
  /** Own notifications (staff_view_notification / student_view_notification). */
  getMine(role) {
    return axiosClient.get(`/notifications/${role}/mine/`);
  },

  /** Staff list w/ notify data (admin_notify_staff). */
  getStaffRecipients() {
    return axiosClient.get("/notifications/staff/recipients/");
  },
  /** Students filtered by course/semester (admin_notify_student drill-down). */
  getStudentRecipients(params = {}) {
    return axiosClient.get("/notifications/student/recipients/", { params });
  },

  sendToStaff(staffId, message) {
    return axiosClient.post("/notifications/staff/send/", {
      id: staffId,
      message,
    });
  },
  sendToStudent(studentId, message) {
    return axiosClient.post("/notifications/student/send/", {
      id: studentId,
      message,
    });
  },
};

export default notificationAPI;
