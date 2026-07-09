import axiosClient from "./axiosClient";

/** Student results: staff add/edit + student view. */
const resultAPI = {
  /** Class picker data for add/edit result (mirrors the attendance picker). */
  getClasses() {
    return axiosClient.get("/results/classes/");
  },
  /** Students of a class: { subject, course, semester, shift } */
  getStudents(params) {
    return axiosClient.get("/results/students/", { params });
  },
  /** Existing result of one student for a subject/session (edit page fetch). */
  fetch(params) {
    return axiosClient.get("/results/fetch/", { params });
  },
  /** Save (staff_add_result) — { student, subject, test, exam, session? }. */
  save(data) {
    return axiosClient.post("/results/", data);
  },
  /** Update (EditResultView). */
  update(data) {
    return axiosClient.put("/results/", data);
  },
  /**
   * Own results by semester (student_view_result):
   * { semesters, selected, rows: [{ subject_name, result|null }] }.
   */
  getMine(params = {}) {
    return axiosClient.get("/results/mine/", { params });
  },
};

export default resultAPI;
