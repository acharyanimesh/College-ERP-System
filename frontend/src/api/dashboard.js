import axiosClient from "./axiosClient";

/**
 * Dashboard statistics endpoints. Each returns the same fields the matching
 * Django view passed as template context (snake_case names kept identical),
 * e.g. admin_home in hod_views.py → adminHome().
 */
const dashboardAPI = {
  /** Admin dashboard counters + chart series (hod_views.admin_home). */
  adminHome() {
    return axiosClient.get("/dashboard/admin/");
  },

  /**
   * Staff dashboard (staff_views.staff_home). `assigned_subjects` is
   * serialized as [{ id, name, courses: [{ name, short_name }] }].
   */
  staffHome() {
    return axiosClient.get("/dashboard/staff/");
  },

  /**
   * Student dashboard (student_views.student_home). `course_subjects` is
   * serialized as [{ subject_name, teacher_name|null }] (teacher already
   * resolved for the student's shift, like cs.staff_for_shift did).
   */
  studentHome() {
    return axiosClient.get("/dashboard/student/");
  },

  /** Librarian dashboard: catalogue + circulation overview. */
  librarianHome() {
    return axiosClient.get("/dashboard/librarian/");
  },
};

export default dashboardAPI;
