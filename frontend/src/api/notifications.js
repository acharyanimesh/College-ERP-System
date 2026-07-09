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
  /** { course_data, search_students } (admin_notify_student landing). */
  getStudentBrowse() {
    return axiosClient.get("/notifications/student/browse/");
  },
  /** { course, semester_data } (notify_student_by_course). */
  getStudentSemesters(courseId) {
    return axiosClient.get(`/notifications/student/courses/${courseId}/semesters/`);
  },
  /** Students of course+semester (notify_student_by_semester). */
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
