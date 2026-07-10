import axiosClient from "./axiosClient";

/** Student results: staff manage (add/edit/view/finalize) + student view. */
const resultAPI = {
  /** Subject -> distinct (course, semester) classes this staff teaches. */
  getClasses() {
    return axiosClient.get("/results/classes/");
  },
  /** Roster + existing marks + finalized flag: { subject, course, semester }. */
  getClassResults(params) {
    return axiosClient.get("/results/class/", { params });
  },
  /** Bulk save — { subject, course, semester, rows: [{ student, unit_test, internal, pre_board, final_grade }] }. */
  saveClassResults(data) {
    return axiosClient.post("/results/class/save/", data);
  },
  /** Lock a class's results — { subject, course, semester }; only when every student is complete. */
  finalize(data) {
    return axiosClient.post("/results/class/finalize/", data);
  },
  /**
   * Own results by semester (student_view_result):
   * { semesters, selected, rows: [{ subject_name, finalized, result|null }] }.
   */
  getMine(params = {}) {
    return axiosClient.get("/results/mine/", { params });
  },
};

export default resultAPI;
