import axiosClient from "./axiosClient";

/**
 * Student-management endpoints (Manage Students navigation, cascade
 * promotion, passed-out records). Endpoint methods are added here as the
 * corresponding pages are converted — components never call axios directly.
 */
const studentAPI = {
  /** Active students, optionally filtered: { course, semester, shift } */
  getAll(params = {}) {
    return axiosClient.get("/students/", { params });
  },

  /** Promote semester N & above for a course (cascade promotion). */
  promote(courseId, fromSemester) {
    return axiosClient.post(`/courses/${courseId}/promote/`, {
      from_semester: fromSemester,
    });
  },
};

export default studentAPI;
