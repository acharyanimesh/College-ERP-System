import axiosClient from "./axiosClient";
import toFormData from "./formData";

/**
 * Student-management endpoints (Manage Students navigation, add/edit,
 * cascade promotion, passed-out records). Components never call axios
 * directly.
 */
const studentAPI = {
  /** Active students, optionally filtered: { course, semester, shift } */
  getAll(params = {}) {
    return axiosClient.get("/students/", { params });
  },

  /** Full details for one student (admin student_details page). */
  get(studentId) {
    return axiosClient.get(`/students/${studentId}/`);
  },

  /** Create a student (multipart: profile_pic). Fields match StudentForm. */
  create(data) {
    return axiosClient.post("/students/", toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** Update a student (multipart: profile_pic). */
  update(studentId, data) {
    return axiosClient.put(`/students/${studentId}/`, toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  delete(studentId) {
    return axiosClient.delete(`/students/${studentId}/`);
  },

  /** Re-send the verification email for a not-yet-verified student. */
  resendVerification(studentId) {
    return axiosClient.post(`/students/${studentId}/resend-verification/`);
  },

  /** Promote semester N & above for a course (cascade promotion). */
  promote(courseId, fromSemester) {
    return axiosClient.post(`/courses/${courseId}/promote/`, {
      from_semester: fromSemester,
    });
  },

  /** Freeze alphabetical roll-number renumbering for a semester. One-way, and
   *  the admin's own password confirms it. */
  lockRollNumbers(courseId, semester, password) {
    return axiosClient.post(
      `/courses/${courseId}/semesters/${semester}/roll-lock/`, { password });
  },

  /* --- Manage Students drill-down (course → semester → shift) --- */

  /** Courses with active-student counts (manage_student). */
  manageCourses() {
    return axiosClient.get("/students/manage/courses/");
  },
  /** { course, total_semesters, semester_data } (manage_student_by_course). */
  manageSemesters(courseId) {
    return axiosClient.get(`/students/manage/courses/${courseId}/semesters/`);
  },
  /** { course, shift_data, is_final_semester } (…_by_course_semester). */
  manageShifts(courseId, semester) {
    return axiosClient.get(
      `/students/manage/courses/${courseId}/semesters/${semester}/shifts/`
    );
  },

  /* --- Passed-out records drill-down (course → session) --- */

  /** Courses with passed-out counts (passed_out_students). */
  passedOutCourses() {
    return axiosClient.get("/students/passed-out/courses/");
  },
  /** { course, session_data, no_session_count } (passed_out_by_course). */
  passedOutSessions(courseId) {
    return axiosClient.get(`/students/passed-out/courses/${courseId}/sessions/`);
  },
  /** Passed-out students of a course+session (passed_out_by_session). */
  getPassedOut(params = {}) {
    return axiosClient.get("/students/passed-out/", { params });
  },
};

export default studentAPI;
