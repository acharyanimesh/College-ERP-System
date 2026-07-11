import axiosClient from "./axiosClient";

/** Admin review queue for Staff/Student email-change requests (see api/auth.js's requestEmailChange). */
const emailChangeRequestsAPI = {
  getAll() {
    return axiosClient.get("/auth/admin/email-change-requests/");
  },
  /** Approves the request, which sends the verification link to the new address. */
  approve(userId) {
    return axiosClient.post(`/auth/admin/email-change-requests/${userId}/approve/`);
  },
  reject(userId) {
    return axiosClient.post(`/auth/admin/email-change-requests/${userId}/reject/`);
  },
};

export default emailChangeRequestsAPI;
