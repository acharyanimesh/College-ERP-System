import axiosClient from "./axiosClient";

/**
 * Attendance endpoints (staff Take / Update / View attendance flows).
 * Endpoint methods are added here as the corresponding pages are converted.
 */
const attendanceAPI = {
  /** Students of a class: { subject, course, semester, shift } */
  getStudents(params) {
    return axiosClient.get("/attendance/students/", { params });
  },

  /** Existing attendance dates for a class; pass include_locked for View. */
  getAttendance(params) {
    return axiosClient.get("/attendance/", { params });
  },

  /** Save a new attendance record. */
  save(payload) {
    return axiosClient.post("/attendance/", payload);
  },

  /** Update (and lock) an existing attendance record. */
  update(attendanceId, payload) {
    return axiosClient.put(`/attendance/${attendanceId}/`, payload);
  },

  /* --- Admin "Fetch Attendance" drill-down --- */

  /** Courses with student counts (admin_view_attendance). */
  adminCourses() {
    return axiosClient.get("/attendance/admin/courses/");
  },
  /** { course, students } of one course (admin_attendance_by_course). */
  adminStudents(courseId) {
    return axiosClient.get(`/attendance/admin/courses/${courseId}/students/`);
  },
  /** { student, attendance_summary } per subject (admin_student_attendance). */
  studentSummary(studentId) {
    return axiosClient.get(`/attendance/admin/students/${studentId}/summary/`);
  },
};

export default attendanceAPI;
