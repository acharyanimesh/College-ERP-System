import axiosClient from "./axiosClient";

/** Courses, subjects and sessions (the Academic Management sidebar group). */

export const courseAPI = {
  getAll() {
    return axiosClient.get("/courses/");
  },
  get(courseId) {
    return axiosClient.get(`/courses/${courseId}/`);
  },
  create(data) {
    return axiosClient.post("/courses/", data);
  },
  update(courseId, data) {
    return axiosClient.put(`/courses/${courseId}/`, data);
  },
  delete(courseId) {
    return axiosClient.delete(`/courses/${courseId}/`);
  },
};

export const subjectAPI = {
  /** Subjects, optionally filtered: { course, semester } */
  getAll(params = {}) {
    return axiosClient.get("/subjects/", { params });
  },
  /** { course, semester_data: [{number, subject_count}] } (manage_subject_by_course). */
  manageSemesters(courseId) {
    return axiosClient.get(`/subjects/manage/courses/${courseId}/semesters/`);
  },
  get(subjectId) {
    return axiosClient.get(`/subjects/${subjectId}/`);
  },
  /**
   * data: { name, code, credit_hours, courses: [{ course, semester }] } —
   * course assignment + per-course semester like add_subject handles.
   */
  create(data) {
    return axiosClient.post("/subjects/", data);
  },
  update(subjectId, data) {
    return axiosClient.put(`/subjects/${subjectId}/`, data);
  },
  delete(subjectId) {
    return axiosClient.delete(`/subjects/${subjectId}/`);
  },
};

export const sessionAPI = {
  getAll() {
    return axiosClient.get("/sessions/");
  },
  get(sessionId) {
    return axiosClient.get(`/sessions/${sessionId}/`);
  },
  create(data) {
    return axiosClient.post("/sessions/", data);
  },
  update(sessionId, data) {
    return axiosClient.put(`/sessions/${sessionId}/`, data);
  },
  delete(sessionId) {
    return axiosClient.delete(`/sessions/${sessionId}/`);
  },
};
