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

  /** Promote semester N & above for a course (cascade promotion). */
  promote(courseId, fromSemester) {
    return axiosClient.post(`/courses/${courseId}/promote/`, {
      from_semester: fromSemester,
    });
  },

  /** Passed-out students, optionally filtered: { course, session } */
  getPassedOut(params = {}) {
    return axiosClient.get("/students/passed-out/", { params });
  },
};

export default studentAPI;
