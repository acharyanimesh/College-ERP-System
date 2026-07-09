import axiosClient from "./axiosClient";

/** Leave applications: staff/student apply + admin review. */
const leaveAPI = {
  /** Own leave history + apply (staff_apply_leave / student_apply_leave). */
  getMine(role) {
    return axiosClient.get(`/leave/${role}/mine/`);
  },
  apply(role, data) {
    return axiosClient.post(`/leave/${role}/mine/`, data);
  },

  /** Admin review (view_staff_leave / view_student_leave). */
  getAll(role) {
    return axiosClient.get(`/leave/${role}/`);
  },
  /** status: 1 approve, -1 reject (same codes the Django views used). */
  setStatus(role, leaveId, status) {
    return axiosClient.post(`/leave/${role}/${leaveId}/status/`, { status });
  },
};

export default leaveAPI;
